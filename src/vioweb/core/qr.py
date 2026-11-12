"""Leitura do QRCode a partir de imagens e PDFs.

O conteúdo do QRCode é binário transportado como texto Latin-1; a recuperação
dos bytes originais segue o mesmo caminho do app oficial::

    dados.decode("utf-8").encode("latin-1")

Dois cuidados importantes na leitura:

* **Só QRCodes contam.** Documentos como a CIN trazem também códigos de barras
  1D (CODE39, CODE128) ao lado do QRCode; aceitar qualquer simbologia faria a
  biblioteca devolver o conteúdo do código de barras errado.
* **Escalonamento de resolução.** Em documentos digitalizados o QRCode costuma
  ocupar poucos pixels e o zbar falha na resolução original. Quando nada é
  encontrado, a imagem é ampliada progressivamente até o QRCode aparecer.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional, Union

from .exceptions import MissingDependencyError, QRCodeNotFoundError
from .formats.envelope import is_vio_or_cin_qr

#: Fatores de ampliação tentados em sequência até o QRCode ser decodificado.
UPSCALE_STEPS = (1, 2, 3, 4)

#: Teto de pixels da imagem ampliada, para não estourar a memória.
MAX_PIXELS = 100_000_000


def _decode_qr_bytes_candidates(raw_text_bytes: bytes) -> list[bytes]:
    """Gera candidatos de bytes originais a partir do buffer retornado pelo zbar.

    O libzbar tenta adivinhar a codificação de QRCodes em modo binário entre
    UTF-8, ISO-8859-1 (Latin-1) e Shift-JIS (CP932), convertendo tudo para UTF-8.
    Testamos Latin-1, CP932 e recuperação híbrida caractere a caractere.
    """
    candidates: list[bytes] = []
    try:
        decoded_str = raw_text_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return [raw_text_bytes]

    # 1) Caminho padrão: libzbar interpretou os bytes como ISO-8859-1
    try:
        candidates.append(decoded_str.encode("latin-1"))
    except UnicodeEncodeError:
        pass

    # 2) Caminho Shift-JIS / CP932: libzbar interpretou sequências binárias como SJIS
    try:
        cp932_bytes = decoded_str.encode("cp932")
        if cp932_bytes not in candidates:
            candidates.append(cp932_bytes)
    except UnicodeEncodeError:
        pass

    # 3) Recuperação híbrida (caso misture codepoints <= 0xFF e CP932)
    try:
        out = bytearray()
        for ch in decoded_str:
            code = ord(ch)
            if code <= 0xFF:
                out.append(code)
            else:
                out.extend(ch.encode("cp932"))
        hybrid = bytes(out)
        if hybrid not in candidates:
            candidates.append(hybrid)
    except UnicodeEncodeError:
        pass

    if raw_text_bytes not in candidates:
        candidates.append(raw_text_bytes)
    return candidates


def _decode_qr_bytes(raw_text_bytes: bytes) -> bytes:
    """Converte o texto do QRCode de volta para os bytes originais (priorizando VIO/CIN)."""
    candidates = _decode_qr_bytes_candidates(raw_text_bytes)
    for cand in candidates:
        if is_vio_or_cin_qr(cand):
            return cand
    return candidates[0] if candidates else raw_text_bytes


def _import_readers():
    try:
        from PIL import Image, ImageOps  # noqa: F401
        from pyzbar.pyzbar import ZBarSymbol, decode  # noqa: F401
    except ImportError as exc:  # pragma: no cover - ambiente sem as libs
        raise MissingDependencyError(
            "leitura de QRCode requer 'pyzbar' e 'Pillow'"
        ) from exc
    return Image, ImageOps, decode, ZBarSymbol


def _other_symbologies(image) -> list[str]:
    """Simbologias não-QR presentes na imagem (usado só na mensagem de erro)."""
    try:
        _Image, _ImageOps, decode, _ZBarSymbol = _import_readers()
        return sorted({symbol.type for symbol in decode(image)})
    except Exception:  # noqa: BLE001 - diagnóstico não pode quebrar a leitura
        return []


def _scaled_variants(gray, factor: int, Image):
    """Versões ampliadas da imagem, uma de cada vez (a memória importa aqui)."""
    if factor == 1:
        yield gray
        return

    size = (gray.width * factor, gray.height * factor)
    for resample in (Image.LANCZOS, Image.NEAREST):
        yield gray.resize(size, resample)


def _candidate_filters(scaled, ImageOps):
    """Gera variações de contraste, nitidez e binarização para facilitar a leitura."""
    yield scaled
    try:
        yield ImageOps.autocontrast(scaled)
    except Exception:
        pass

    try:
        from PIL import ImageFilter

        sharpened = scaled.filter(ImageFilter.SHARPEN)
        yield sharpened
    except Exception:
        pass

    try:
        import cv2
        import numpy as np
        from PIL import Image

        arr = np.array(scaled)
        _, otsu = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        yield Image.fromarray(otsu)

        adapt = cv2.adaptiveThreshold(
            arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 5
        )
        yield Image.fromarray(adapt)
    except Exception:
        pass


def _region_crops(gray):
    """Recorta quadrantes estratégicos onde QRCodes de CRLV-e, CNH e ATPV-e costumam ficar."""
    w, h = gray.width, gray.height
    if w < 200 or h < 200:
        return
    # Canto superior direito (padrão CRLV-e e ATPV-e), superior esquerdo, metade superior e centro
    boxes = [
        (int(w * 0.40), 0, w, int(h * 0.60)),
        (0, 0, int(w * 0.65), int(h * 0.60)),
        (0, 0, w, int(h * 0.55)),
        (int(w * 0.15), int(h * 0.15), int(w * 0.85), int(h * 0.85)),
        (0, int(h * 0.45), w, h),
    ]
    for box in boxes:
        try:
            yield gray.crop(box)
        except Exception:
            continue


def decode_qr(image, *, upscale_steps: tuple[int, ...] = UPSCALE_STEPS) -> Optional[bytes]:
    """Decodifica o QRCode principal de uma ``PIL.Image``, priorizando envelopes VIO/CIN."""
    from PIL import Image, ImageOps

    fallback_non_vio: Optional[bytes] = None

    # Se a imagem possuir canal alpha transparente (comum em prints recortados), compõe em fundo branco
    if getattr(image, "mode", None) in ("RGBA", "LA") or (
        getattr(image, "mode", None) == "P" and "transparency" in getattr(image, "info", {})
    ):
        rgba = image.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        image = Image.alpha_composite(bg, rgba).convert("RGB")

    gray = image if image.mode == "L" else ImageOps.grayscale(image)
    base_pixels = gray.width * gray.height

    # 0) Leitor primário C++ (zxing-cpp): preserva bytes binários exatos e funciona sem libzbar
    try:
        import zxingcpp

        def _scan_zxing(pil_img) -> Optional[bytes]:
            nonlocal fallback_non_vio
            bars = zxingcpp.read_barcodes(
                pil_img,
                formats=zxingcpp.BarcodeFormat.QRCode,
                try_rotate=True,
                try_downscale=True,
                try_invert=True,
            )
            for bar in bars:
                raw_b = bytes(bar.bytes)
                for cand in _decode_qr_bytes_candidates(raw_b):
                    if is_vio_or_cin_qr(cand):
                        return cand
                    if fallback_non_vio is None and cand:
                        fallback_non_vio = cand
            return None

        hit = _scan_zxing(gray)
        if hit is not None:
            return hit

        for factor in (2, 3):
            if base_pixels * factor * factor <= MAX_PIXELS:
                for scaled in _scaled_variants(gray, factor, Image):
                    hit = _scan_zxing(scaled)
                    if hit is not None:
                        return hit

        for crop in _region_crops(gray):
            hit = _scan_zxing(crop)
            if hit is not None:
                return hit
            crop_pixels = crop.width * crop.height
            if crop_pixels * 4 <= MAX_PIXELS:
                for scaled in _scaled_variants(crop, 2, Image):
                    hit = _scan_zxing(scaled)
                    if hit is not None:
                        return hit
    except Exception:
        pass

    # 1) Leitor secundário (pyzbar / libzbar) com escalonamento e filtros
    try:
        _Image, _ImageOps, decode, ZBarSymbol = _import_readers()

        def _scan_symbols(found_symbols) -> Optional[bytes]:
            nonlocal fallback_non_vio
            for sym in found_symbols:
                for cand in _decode_qr_bytes_candidates(sym.data):
                    if is_vio_or_cin_qr(cand):
                        return cand
                    if fallback_non_vio is None:
                        fallback_non_vio = cand
            return None

        # Passada 1: Escalonamento progressivo na imagem inteira (rápida: normal + autocontrast)
        for factor in upscale_steps:
            if factor > 1 and base_pixels * factor * factor > MAX_PIXELS:
                break

            for scaled in _scaled_variants(gray, factor, Image):
                for candidate in (scaled, ImageOps.autocontrast(scaled)):
                    found = decode(candidate, symbols=[ZBarSymbol.QRCODE])
                    if found:
                        hit = _scan_symbols(found)
                        if hit is not None:
                            return hit

        # Passada 2: Filtros avançados (nitidez, Otsu, limiar adaptativo) em 1x e 2x
        for factor in (1, 2):
            if factor > 1 and base_pixels * factor * factor > MAX_PIXELS:
                break
            for scaled in _scaled_variants(gray, factor, Image):
                for candidate in _candidate_filters(scaled, ImageOps):
                    found = decode(candidate, symbols=[ZBarSymbol.QRCODE])
                    if found:
                        hit = _scan_symbols(found)
                        if hit is not None:
                            return hit

        # Passada 3: Recorte de quadrantes com ampliação (ideal para prints de tela inteira)
        for crop in _region_crops(gray):
            crop_pixels = crop.width * crop.height
            for factor in (2, 3):
                if crop_pixels * factor * factor > MAX_PIXELS:
                    continue
                for scaled in _scaled_variants(crop, factor, Image):
                    for candidate in _candidate_filters(scaled, ImageOps):
                        found = decode(candidate, symbols=[ZBarSymbol.QRCODE])
                        if found:
                            hit = _scan_symbols(found)
                            if hit is not None:
                                return hit
    except Exception:
        pass

    # Fallback com OpenCV caso pyzbar não localize
    try:
        import cv2
        import numpy as np

        np_img = np.array(gray)
        detector = cv2.QRCodeDetector()
        val, points, _ = detector.detectAndDecode(np_img)
        if val:
            cand = _decode_qr_bytes(val.encode("latin-1"))
            if is_vio_or_cin_qr(cand):
                return cand
            if fallback_non_vio is None:
                fallback_non_vio = cand
    except Exception:
        pass

    return fallback_non_vio


def _open_image(source: Union[bytes, bytearray, str, Path]):
    from PIL import Image

    if isinstance(source, (bytes, bytearray)):
        return Image.open(io.BytesIO(source))
    if isinstance(source, (str, Path)):
        return Image.open(str(source))
    return source  # assume PIL.Image


def read_qr_from_image(source: Union[bytes, bytearray, str, Path]) -> bytes:
    """Lê o primeiro QRCode de uma imagem (caminho, bytes ou ``PIL.Image``)."""
    image = _open_image(source)

    data = decode_qr(image)
    if data is None:
        raise QRCodeNotFoundError(_not_found_message(image))
    return data


def _not_found_message(image) -> str:
    others = _other_symbologies(image)
    if others:
        return (
            "nenhum QRCode encontrado; a imagem contém apenas "
            f"código(s) de barras {', '.join(others)}"
        )
    return "nenhum QRCode encontrado na imagem"


def read_qr_from_pdf(source: Union[str, Path, bytes, bytearray], *, dpi: int = 300) -> bytes:
    """Lê o QRCode principal de um PDF (caminho ou bytes), priorizando envelopes VIO/CIN."""
    try:
        import pymupdf
    except ImportError:
        pymupdf = None

    fallback_non_vio: Optional[bytes] = None

    if pymupdf is not None:
        from PIL import Image

        if isinstance(source, (bytes, bytearray)):
            doc = pymupdf.open(stream=source, filetype="pdf")
        else:
            doc = pymupdf.open(str(source))

        try:
            # 1) Tenta primeiro extrair imagens embutidas diretamente nas páginas (muito rápido e sem perda)
            for page in doc:
                try:
                    for img_info in page.get_images(full=True):
                        xref = img_info[0]
                        base_img = doc.extract_image(xref)
                        if base_img and base_img.get("image"):
                            pil_img = Image.open(io.BytesIO(base_img["image"]))
                            data = decode_qr(pil_img)
                            if data is not None:
                                if is_vio_or_cin_qr(data):
                                    return data
                                if fallback_non_vio is None:
                                    fallback_non_vio = data
                except Exception:
                    continue

            # 2) Renderiza cada página em alta resolução (300 DPI e 600 DPI)
            for render_dpi in (dpi, dpi * 2):
                zoom = render_dpi / 72
                matrix = pymupdf.Matrix(zoom, zoom)
                for page in doc:
                    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                    image = Image.frombytes(
                        "RGB", (pixmap.width, pixmap.height), pixmap.samples
                    )
                    data = decode_qr(image)
                    if data is not None:
                        if is_vio_or_cin_qr(data):
                            return data
                        if fallback_non_vio is None:
                            fallback_non_vio = data
        finally:
            doc.close()

        if fallback_non_vio is not None:
            return fallback_non_vio
        raise QRCodeNotFoundError("nenhum QRCode encontrado no PDF")

    # fallback: pdf2image
    try:
        from pdf2image import convert_from_path, convert_from_bytes
    except ImportError as exc:
        raise MissingDependencyError(
            "leitura de PDF requer 'PyMuPDF' ou 'pdf2image'"
        ) from exc

    for render_dpi in (dpi, dpi * 2):
        images = (
            convert_from_bytes(source, dpi=render_dpi)
            if isinstance(source, (bytes, bytearray))
            else convert_from_path(str(source), dpi=render_dpi)
        )
        for image in images:
            data = decode_qr(image)
            if data is not None:
                if is_vio_or_cin_qr(data):
                    return data
                if fallback_non_vio is None:
                    fallback_non_vio = data

    if fallback_non_vio is not None:
        return fallback_non_vio
    raise QRCodeNotFoundError("nenhum QRCode encontrado no PDF")

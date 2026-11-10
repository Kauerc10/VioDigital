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

#: Fatores de ampliação tentados em sequência até o QRCode ser decodificado.
UPSCALE_STEPS = (1, 2, 3, 4)

#: Teto de pixels da imagem ampliada, para não estourar a memória.
MAX_PIXELS = 100_000_000


def _decode_qr_bytes(raw_text_bytes: bytes) -> bytes:
    """Converte o texto do QRCode de volta para os bytes originais."""
    try:
        return raw_text_bytes.decode("utf-8").encode("latin-1")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return raw_text_bytes


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


def decode_qr(image, *, upscale_steps: tuple[int, ...] = UPSCALE_STEPS) -> Optional[bytes]:
    """Decodifica o primeiro QRCode de uma ``PIL.Image``."""
    try:
        Image, ImageOps, decode, ZBarSymbol = _import_readers()
        gray = image if image.mode == "L" else ImageOps.grayscale(image)
        base_pixels = gray.width * gray.height

        for factor in upscale_steps:
            if factor > 1 and base_pixels * factor * factor > MAX_PIXELS:
                break

            for scaled in _scaled_variants(gray, factor, Image):
                for candidate in (scaled, ImageOps.autocontrast(scaled)):
                    found = decode(candidate, symbols=[ZBarSymbol.QRCODE])
                    if found:
                        return _decode_qr_bytes(found[0].data)
    except Exception:
        gray = image if getattr(image, "mode", None) == "L" else image.convert("L")

    # Fallback com OpenCV caso pyzbar não localize
    try:
        import cv2
        import numpy as np

        np_img = np.array(gray)
        detector = cv2.QRCodeDetector()
        val, points, _ = detector.detectAndDecode(np_img)
        if val:
            return _decode_qr_bytes(val.encode("latin-1"))
    except Exception:
        pass

    return None


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
    """Lê o primeiro QRCode de um PDF (caminho ou bytes), renderizando as páginas em memória."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        fitz = None

    if fitz is not None:
        from PIL import Image

        if isinstance(source, (bytes, bytearray)):
            doc = fitz.open(stream=source, filetype="pdf")
        else:
            doc = fitz.open(str(source))

        try:
            for render_dpi in (dpi, dpi * 2):
                zoom = render_dpi / 72
                matrix = fitz.Matrix(zoom, zoom)
                for page in doc:
                    pixmap = page.get_pixmap(matrix=matrix)
                    image = Image.frombytes(
                        "RGB", (pixmap.width, pixmap.height), pixmap.samples
                    )
                    data = decode_qr(image)
                    if data is not None:
                        return data
        finally:
            doc.close()
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
                return data
    raise QRCodeNotFoundError("nenhum QRCode encontrado no PDF")

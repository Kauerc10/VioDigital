import io
import pymupdf
import pytest
import qrcode
from PIL import Image

from vioweb.core import DigitalDocumentChecker
from vioweb.core.documents.crlv import CRLVData
from vioweb.core.exceptions import QRCodeNotFoundError
from tests.conftest import build_multiblock_qr
from tests.test_crlv import CRLV_FIELDS, TIMESTAMP


def _create_qr_image(payload: bytes) -> Image.Image:
    # Codifica como latin-1 para preservar os bytes brutos no QRCode
    text = payload.decode("latin-1")
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def _create_crlv_pdf(qr_image: Image.Image) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4

    # Salva imagem do QR em buffer e insere na página
    img_buf = io.BytesIO()
    qr_image.save(img_buf, format="PNG")
    img_bytes = img_buf.getvalue()

    # Retângulo no topo/centro
    rect = pymupdf.Rect(100, 100, 300, 300)
    page.insert_image(rect, stream=img_bytes)
    page.insert_text((100, 350), "CERTIFICADO DE REGISTRO E LICENCIAMENTO DE VEICULO - ELETRONICO", fontsize=12)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_pipeline_read_qr_from_image(rsa_material, cert_store, crlv_template_store):
    qr_bytes = build_multiblock_qr(
        CRLV_FIELDS,
        version=4,
        template_id=70,
        timestamp=TIMESTAMP,
        sign=rsa_material["sign"],
    )

    qr_img = _create_qr_image(qr_bytes)
    img_buf = io.BytesIO()
    qr_img.save(img_buf, format="PNG")

    checker = DigitalDocumentChecker(certificates=cert_store, templates=crlv_template_store)
    result = checker.parse_image(img_buf.getvalue())

    assert result.is_parsed
    assert result.document_type == "crlv"
    assert result.is_authentic is True
    assert isinstance(result.data, CRLVData)
    assert result.data.placa == "ABC1D23"
    assert result.data.renavam == "11223344556"


def test_pipeline_read_qr_from_pdf_in_memory(rsa_material, cert_store, crlv_template_store):
    qr_bytes = build_multiblock_qr(
        CRLV_FIELDS,
        version=4,
        template_id=70,
        timestamp=TIMESTAMP,
        sign=rsa_material["sign"],
    )

    qr_img = _create_qr_image(qr_bytes)
    pdf_bytes = _create_crlv_pdf(qr_img)

    checker = DigitalDocumentChecker(certificates=cert_store, templates=crlv_template_store)
    result = checker.parse_pdf(pdf_bytes, dpi=300)

    assert result.is_parsed
    assert result.document_type == "crlv"
    assert result.is_authentic is True
    assert result.data.chassi == "9BWZZZ377VT004251"
    assert result.data.proprietario == "JOAO DA SILVA SAO PAULO"


def test_pipeline_parse_file_auto_detect(rsa_material, cert_store, crlv_template_store):
    qr_bytes = build_multiblock_qr(
        CRLV_FIELDS,
        version=4,
        template_id=70,
        timestamp=TIMESTAMP,
        sign=rsa_material["sign"],
    )

    qr_img = _create_qr_image(qr_bytes)
    pdf_bytes = _create_crlv_pdf(qr_img)

    checker = DigitalDocumentChecker(certificates=cert_store, templates=crlv_template_store)

    # Detecta PDF por assinatura de bytes (%PDF)
    res_pdf = checker.parse_file(pdf_bytes)
    assert res_pdf.is_parsed
    assert res_pdf.document_type == "crlv"

    # Detecta Imagem
    img_buf = io.BytesIO()
    qr_img.save(img_buf, format="PNG")
    res_img = checker.parse_file(img_buf.getvalue())
    assert res_img.is_parsed
    assert res_img.document_type == "crlv"


def test_pipeline_no_qr_found():
    # Cria uma imagem em branco sem QR Code
    blank = Image.new("RGB", (300, 300), color="white")
    buf = io.BytesIO()
    blank.save(buf, format="PNG")

    checker = DigitalDocumentChecker()
    with pytest.raises(QRCodeNotFoundError):
        checker.parse_image(buf.getvalue())


def test_pipeline_multi_qr_prioritizes_vio_over_url_qr(
    rsa_material, cert_store, crlv_template_store
):
    """Simula um print de documento com 2 QR Codes: um Selo Digital (URL) grande
    e o QR Code VIO denso do CRLV-e menor no canto superior direito.
    O leitor deve ignorar a URL e extrair o envelope VIO do CRLV-e.
    """
    url_qr = _create_qr_image(b"https://selo.tjsc.jus.br/confere/ABC123456")
    vio_bytes = build_multiblock_qr(
        CRLV_FIELDS,
        version=4,
        template_id=70,
        timestamp=TIMESTAMP,
        sign=rsa_material["sign"],
    )
    vio_qr = _create_qr_image(vio_bytes)
    # Redimensiona o QR VIO para simular print de tela de menor resolução
    vio_qr_small = vio_qr.resize((220, 220), Image.Resampling.BILINEAR)

    canvas = Image.new("RGB", (1000, 700), color="white")
    canvas.paste(url_qr.resize((260, 260)), (40, 40))
    canvas.paste(vio_qr_small, (720, 40))

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")

    checker = DigitalDocumentChecker(
        certificates=cert_store, templates=crlv_template_store
    )
    result = checker.parse_image(buf.getvalue())

    assert result.is_parsed is True
    assert result.document_type == "crlv"
    assert result.is_authentic is True
    assert isinstance(result.data, CRLVData)
    assert result.data.placa_formatada == "ABC1D23"


def test_pipeline_external_qr_fallback():
    """Quando a imagem contém APENAS um QR Code de URL externa (ex.: Selo Digital TJSC),
    o sistema não deve falhar com 'versão de envelope não suportada: 115', mas retornar
    document_type='external_qr' com diagnóstico claro.
    """
    url_qr = _create_qr_image(b"https://selo.tjsc.jus.br/confere?selo=XYZ987")
    buf = io.BytesIO()
    url_qr.save(buf, format="PNG")

    checker = DigitalDocumentChecker()
    result = checker.parse_image(buf.getvalue())

    assert result.is_parsed is True
    assert result.is_authentic is False
    assert result.document_type == "external_qr"
    assert "selo.tjsc.jus.br" in result.fields.get("dominio", "")
    assert result.warnings


def test_qr_shift_jis_recovery():
    """Garante que bytes binários interpretados como Shift-JIS pelo libzbar sejam recuperados."""
    from vioweb.core.qr import _decode_qr_bytes_candidates

    # Sequência binária com par Shift-JIS válido (0x82 0xA0 = 'あ' em cp932)
    original_binary = b"d\xb5\x8d\xc3\x02\x00\x04\x82\xa0\x83\x41test"
    sjis_decoded_str = original_binary.decode("cp932")
    zbar_utf8_bytes = sjis_decoded_str.encode("utf-8")

    candidates = _decode_qr_bytes_candidates(zbar_utf8_bytes)
    assert original_binary in candidates


def test_qr_transport_latin1_utf8_recovery():
    """Garante que bytes binários transportados como Latin-1 em UTF-8 sejam recuperados via _decode_qr_bytes."""
    from vioweb.core.qr import _decode_qr_bytes, _decode_qr_bytes_candidates

    # Envelope VIO válido com bytes > 0x7F (cabeçalho binário v4/v5 Serpro)
    original_envelope = b"d\xb5\x8d\xc3\x02\x00\x04\x90\xaa\xbb\xcc\xdd"
    transport_utf8 = original_envelope.decode("latin-1").encode("utf-8")

    assert transport_utf8 != original_envelope
    candidates = _decode_qr_bytes_candidates(transport_utf8)
    assert original_envelope in candidates
    recovered = _decode_qr_bytes(transport_utf8)
    assert recovered == original_envelope

import io
import fitz
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
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    # Salva imagem do QR em buffer e insere na página
    img_buf = io.BytesIO()
    qr_image.save(img_buf, format="PNG")
    img_bytes = img_buf.getvalue()

    # Retângulo no topo/centro
    rect = fitz.Rect(100, 100, 300, 300)
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

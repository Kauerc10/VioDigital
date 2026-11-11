import io
from fastapi.testclient import TestClient
from PIL import Image

from vioweb.api.app import app
from tests.conftest import build_multiblock_qr
from tests.test_crlv import CRLV_FIELDS, TIMESTAMP
from tests.test_pipeline import _create_crlv_pdf, _create_qr_image

client = TestClient(app)


def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "VioWeb", "version": "0.1.0"}


def test_api_root_serves_html():
    res = client.get("/")
    assert res.status_code == 200
    assert "VioWeb" in res.text
    assert "dropzone" in res.text


def test_api_verify_document_crlv(rsa_material, cert_store, crlv_template_store, monkeypatch):
    from vioweb.core import DigitalDocumentChecker
    from vioweb.api import app as api_module

    # Injeta checker configurado com chaves de teste
    test_checker = DigitalDocumentChecker(certificates=cert_store, templates=crlv_template_store)
    monkeypatch.setattr(api_module, "_checker", test_checker)

    qr_bytes = build_multiblock_qr(
        CRLV_FIELDS,
        version=4,
        template_id=70,
        timestamp=TIMESTAMP,
        sign=rsa_material["sign"],
    )
    qr_img = _create_qr_image(qr_bytes)
    pdf_bytes = _create_crlv_pdf(qr_img)

    response = client.post(
        "/api/documents/verify",
        files={"file": ("crlv.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_parsed"] is True
    assert data["is_authentic"] is True
    assert data["document_type"] == "crlv"
    assert data["formatted"]["placa_formatada"] == "ABC1D23"
    assert data["formatted"]["renavam_formatado"] == "11223344556"
    assert data["formatted"]["chassi"] == "9BWZZZ377VT004251"
    assert data["formatted"]["cpf_cnpj_formatado"] == "123.456.789-09"
    assert data["formatted"]["proprietario"] == "JOAO DA SILVA SAO PAULO"


def test_api_verify_no_qr_found():
    blank = Image.new("RGB", (200, 200), color="white")
    buf = io.BytesIO()
    blank.save(buf, format="PNG")

    response = client.post(
        "/api/documents/verify",
        files={"file": ("blank.png", buf.getvalue(), "image/png")},
    )

    assert response.status_code == 422
    data = response.json()
    assert data["is_parsed"] is False
    assert data["error"] == "QR_NOT_FOUND"


def test_api_verify_document_with_photo(rsa_material, cert_store, monkeypatch):
    from vioweb.core import DigitalDocumentChecker
    from vioweb.core.models import Photo, DocumentResult
    from vioweb.core.documents.cnh import CNHData
    from vioweb.api import app as api_module

    fake_result = DocumentResult(
        raw=b"test",
        is_parsed=True,
        is_authentic=True,
        document_type="cnh",
        document_name="CNH Digital",
        data=CNHData(nome="CONDUTOR TESTE", cpf="12345678909", categoria="B"),
        fields={"nome": "CONDUTOR TESTE", "cpf": "12345678909"},
        photo=Photo(data=b"\x89PNG\r\n\x1a\nfake_png", format="PNG"),
    )

    class MockChecker:
        def parse_file(self, content):
            return fake_result

    monkeypatch.setattr(api_module, "_checker", MockChecker())

    response = client.post(
        "/api/documents/verify",
        files={"file": ("cnh.png", b"fakecontent", "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_parsed"] is True
    assert data["photo_b64"] is not None
    assert "data:image/png;base64," in data["photo_b64"]


def test_api_verify_cnh_complete_fields(monkeypatch):
    from vioweb.core.models import DocumentResult
    from vioweb.core.documents.cnh import CNHData
    from vioweb.api import app as api_module

    fake_result = DocumentResult(
        raw=b"test",
        is_parsed=True,
        is_authentic=True,
        document_type="cnh",
        document_name="CNH Digital",
        data=CNHData(
            nome="JOAO VITOR DIAS",
            cpf="09854034976",
            categoria="AB",
            identidade="123456 SSP/SC",
            data_nascimento="15/02/1995",
            filiacao_mae="MARIA DIAS",
            filiacao_pai="JOSE DIAS",
            numero_registro="07260723692",
            data_validade="15/02/2034",
            data_emissao="19/02/2024",
            data_primeira_habilitacao="15/02/2013",
            local_emissao="FLORIANOPOLIS",
            uf_emissao="SC",
            numero_renach="SC195462467",
            numero_validacao_cnh="99887766",
            observacoes="EAR",
        ),
        fields={"nome": "JOAO VITOR DIAS", "cpf": "09854034976"},
    )

    class MockChecker:
        def parse_file(self, content):
            return fake_result

    monkeypatch.setattr(api_module, "_checker", MockChecker())

    response = client.post(
        "/api/documents/verify",
        files={"file": ("cnh.pdf", b"pdfcontent", "application/pdf")},
    )

    assert response.status_code == 200
    res = response.json()
    fmt = res["formatted"]
    assert fmt["nome"] == "JOAO VITOR DIAS"
    assert fmt["cpf_formatado"] == "098.540.349-76"
    assert fmt["categoria"] == "AB"
    assert fmt["identidade"] == "123456 SSP/SC"
    assert fmt["data_nascimento"] == "15/02/1995"
    assert fmt["filiacao_mae"] == "MARIA DIAS"
    assert fmt["filiacao_pai"] == "JOSE DIAS"
    assert fmt["data_primeira_habilitacao"] == "15/02/2013"
    assert fmt["observacoes"] == "EAR"
    assert fmt["numero_validacao_cnh"] == "99887766"


def test_api_verify_atpv_complete_fields(monkeypatch):
    from vioweb.core.models import DocumentResult
    from vioweb.core.documents.atpv import ATPVData
    from vioweb.api import app as api_module

    fake_result = DocumentResult(
        raw=b"test",
        is_parsed=True,
        is_authentic=True,
        document_type="atpv",
        document_name="ATPVe",
        data=ATPVData(
            numero_atpv="00012345678",
            placa="abc1d23",
            renavam="11223344556",
            chassi="9BWZZZ377VT004251",
            valor_venda="R$ 85.000,00",
            local_venda="FLORIANOPOLIS",
            data_venda="10/11/2026",
            numero_crv="9876543210",
            codigo_seguranca_crv="12345678901",
            uf_emissao_crv="SC",
            data_emissao_crv="05/01/2024",
            marca_modelo="VW/T-CROSS HIGHLINE",
            cor="CINZA",
            ano_fabricacao="2023",
            ano_modelo="2024",
            kilometragem_hodometro="32500",
            nome_vendedor="CARLOS VENDEDOR SILVA",
            documento_vendedor="09854034976",
            email_vendedor="carlos@email.com",
            municipio_vendedor="FLORIANOPOLIS",
            uf_vendedor="SC",
            nome_comprador="MARCOS COMPRADOR SOUZA",
            documento_comprador="12345678909",
            email_comprador="marcos@email.com",
            municipio_comprador="SAO JOSE",
            uf_comprador="SC",
        ),
        fields={"numero_atpv": "00012345678", "placa": "ABC1D23"},
    )

    class MockChecker:
        def parse_file(self, content):
            return fake_result

    monkeypatch.setattr(api_module, "_checker", MockChecker())

    response = client.post(
        "/api/documents/verify",
        files={"file": ("atpv.png", b"imgcontent", "image/png")},
    )

    assert response.status_code == 200
    res = response.json()
    assert res["document_type"] == "atpv"
    fmt = res["formatted"]
    assert fmt["numero_atpv"] == "00012345678"
    assert fmt["placa_formatada"] == "ABC1D23"
    assert fmt["renavam_formatado"] == "11223344556"
    assert fmt["ano_fabricacao_modelo"] == "2023/2024"
    assert fmt["valor_venda"] == "R$ 85.000,00"
    assert fmt["nome_vendedor"] == "CARLOS VENDEDOR SILVA"
    assert fmt["documento_vendedor_formatado"] == "098.540.349-76"
    assert fmt["nome_comprador"] == "MARCOS COMPRADOR SOUZA"
    assert fmt["documento_comprador_formatado"] == "123.456.789-09"

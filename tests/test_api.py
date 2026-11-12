import io
from fastapi.testclient import TestClient
from PIL import Image

from viodigital.api.app import app
from tests.conftest import build_multiblock_qr
from tests.test_crlv import CRLV_FIELDS, TIMESTAMP
from tests.test_pipeline import _create_crlv_pdf, _create_qr_image

client = TestClient(app)


def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "VioDigital", "version": "0.2.0"}


def test_api_root_serves_html():
    res = client.get("/")
    assert res.status_code == 200
    assert "VioDigital" in res.text
    assert "dropzone" in res.text


def test_api_verify_document_crlv(rsa_material, cert_store, crlv_template_store, monkeypatch):
    from viodigital.core import DigitalDocumentChecker
    from viodigital.api import app as api_module

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
    from viodigital.core.models import Photo, DocumentResult
    from viodigital.core.documents.cnh import CNHData
    from viodigital.api import app as api_module

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
    from viodigital.core.models import DocumentResult
    from viodigital.core.documents.cnh import CNHData
    from viodigital.api import app as api_module

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
    from viodigital.core.models import DocumentResult
    from viodigital.core.documents.atpv import ATPVData
    from viodigital.api import app as api_module

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


def test_api_templates_catalog():
    res = client.get("/api/templates")
    assert res.status_code == 200
    data = res.json()
    assert data["total_templates"] >= 161
    assert isinstance(data["categories"], list)
    assert len(data["categories"]) >= 5


def test_api_verify_generic_vio_template_with_photo_and_masks(monkeypatch):
    from viodigital.core.models import DocumentResult, Photo
    from viodigital.core.documents.base import DocumentData
    from viodigital.api import app as api_module

    fake_fields = {
        "nome": "MARINHEIRO TESTE",
        "cpf": "09854034976",
        "cnpj": "12345678000199",
        "placa": "abc1d23",
        "numero_inscricao": "4012345678",
        "nome_embarcacao": "VENTO SUL I",
    }
    fake_result = DocumentResult(
        raw=b"test",
        is_parsed=True,
        is_authentic=True,
        template_id=116,
        template_name="TIE-Título de Inscrição de Embarcação",
        document_type="generic",
        document_name="TIE-Título de Inscrição de Embarcação",
        data=DocumentData(raw_fields=list(fake_fields.values()), fields=fake_fields),
        fields=fake_fields,
        photo=Photo(data=b"BPG\xfb\x00\x01fake_bpg_bytes", format="BPG"),
    )

    class MockChecker:
        def parse_file(self, content):
            return fake_result

    monkeypatch.setattr(api_module, "_checker", MockChecker())

    response = client.post(
        "/api/documents/verify",
        files={"file": ("tie.png", b"imgcontent", "image/png")},
    )

    assert response.status_code == 200
    res = response.json()
    assert res["document_type"] == "generic"
    assert res["photo_b64"] is not None
    assert res["photo_b64"].startswith("data:image/bpg;base64,")
    fmt = res["formatted"]
    assert fmt["cpf"] == "098.540.349-76"
    assert fmt["cnpj"] == "12.345.678/0001-99"
    assert fmt["placa"] == "ABC1D23"
    assert fmt["nome_embarcacao"] == "VENTO SUL I"


def test_api_dedicated_pages_and_seo_routes():
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert "https://github.com/Kauerc10/VioDigital" in html
    assert 'href="/documentos"' in html
    assert 'href="/apoiar"' in html
    assert 'href="/privacidade"' in html

    docs_page = client.get("/documentos")
    assert docs_page.status_code == 200
    assert "Todos os 161 Documentos Oficiais Suportados" in docs_page.text

    apoiar_page = client.get("/apoiar")
    assert apoiar_page.status_code == 200
    assert "Apoie o VioDigital" in apoiar_page.text

    priv_page = client.get("/privacidade")
    assert priv_page.status_code == 200
    assert "LGPD" in priv_page.text

    for slug, expected in [
        ("crlv", "CRLV-e Digital"),
        ("cnh", "CNH Digital"),
        ("atpv", "ATPV-e"),
        ("cin", "Carteira de Identidade Nacional"),
        ("tie-marinha", "Marinha do Brasil"),
    ]:
        seo_page = client.get(f"/validar-{slug}")
        assert seo_page.status_code == 200
        assert expected in seo_page.text
        assert f'href="https://viodigital.com.br/validar-{slug}"' in seo_page.text


def test_api_seo_endpoints_and_metadata():
    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    assert "Sitemap: https://viodigital.com.br/sitemap.xml" in robots.text
    robots_head = client.head("/robots.txt")
    assert robots_head.status_code == 200

    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert "<loc>https://viodigital.com.br/</loc>" in sitemap.text
    sitemap_head = client.head("/sitemap.xml")
    assert sitemap_head.status_code == 200

    llms = client.get("/llms.txt")
    assert llms.status_code == 200
    assert "VioDigital" in llms.text
    llms_head = client.head("/llms.txt")
    assert llms_head.status_code == 200

    # Custom 404 handler
    not_found_html = client.get("/non-existent-page-url")
    assert not_found_html.status_code == 404
    assert "404" in not_found_html.text

    not_found_api = client.get("/api/non-existent-endpoint")
    assert not_found_api.status_code == 404
    assert not_found_api.json()["error"] == "NOT_FOUND"

    root = client.get("/")
    assert root.status_code == 200
    assert 'property="og:title"' in root.text
    assert 'name="twitter:card"' in root.text
    assert 'application/ld+json' in root.text
    assert 'id="seo-faq-section"' in root.text


def test_api_upload_payload_too_large(monkeypatch):
    from viodigital.api import app as api_module

    # Reduz temporariamente o limite para testar 413
    monkeypatch.setattr(api_module, "MAX_UPLOAD_SIZE", 100)
    response = client.post(
        "/api/documents/verify",
        files={"file": ("large.bin", b"X" * 200, "application/octet-stream")},
    )
    assert response.status_code == 413
    data = response.json()
    assert data["error"] == "PAYLOAD_TOO_LARGE"


def test_api_error_500_sanitized(monkeypatch):
    from viodigital.api import app as api_module

    def _boom(_):
        raise ValueError("sensitive_internal_database_string")

    monkeypatch.setattr(api_module._checker, "parse_file", _boom)
    response = client.post(
        "/api/documents/verify",
        files={"file": ("test.png", b"test_content", "image/png")},
    )
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "SERVER_ERROR"
    # Garante que detalhes sensíveis internos não vazaram na mensagem
    assert "sensitive_internal_database_string" not in data["message"]
    assert "Erro interno" in data["message"]


def test_api_cors_no_credentials():
    response = client.options(
        "/api/documents/verify",
        headers={
            "Origin": "https://external.site",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers.get("access-control-allow-credentials") is None or response.headers.get("access-control-allow-credentials") == "false"


def test_api_csp_strict_no_unsafe_eval():
    response = client.get("/")
    assert response.status_code == 200
    csp = response.headers.get("Content-Security-Policy", "")
    assert "wasm-unsafe-eval" in csp
    assert "'unsafe-eval'" not in csp


def test_ensure_runtime_assets_provisions_correctly(tmp_path):
    from viodigital.build_static import ensure_runtime_assets

    fake_web = tmp_path / "web"
    fake_web.mkdir(parents=True)
    ensure_runtime_assets(fake_web, download=False)

    wheels_dir = fake_web / "static" / "wheels"
    assert wheels_dir.exists()
    assert bool(list(wheels_dir.glob("viodigital-*.whl")))


def test_backwards_compatible_vioweb_shim():
    """Garante que importações legadas via vioweb continuem funcionando perfeitamente."""
    import vioweb
    from vioweb.core import DigitalDocumentChecker as LegacyChecker, present as legacy_present
    from vioweb.api.app import app as legacy_app
    from viodigital.core import DigitalDocumentChecker as ModernChecker
    from viodigital.api.app import app as modern_app

    assert LegacyChecker is ModernChecker
    assert legacy_app is modern_app
    assert hasattr(vioweb, "__version__")
    checker = LegacyChecker()
    assert checker is not None

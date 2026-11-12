from __future__ import annotations

import functools
import http.server
import threading
from pathlib import Path
from typing import List

import pytest
from playwright.sync_api import sync_playwright

from vioweb.build_static import build


class CSPStaticHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Handler HTTP local que emula os headers de produção definidos em vercel.json."""

    def end_headers(self):
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; connect-src 'self'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval' blob:; worker-src 'self' blob:; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; font-src 'self';",
        )
        self.send_header("Permissions-Policy", "camera=(self)")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()


@pytest.fixture(scope="module")
def static_server(tmp_path_factory):
    """Gera o build estático e sobe um servidor HTTP local para testes E2E."""
    dist_dir = build()

    handler = functools.partial(CSPStaticHTTPRequestHandler, directory=str(dist_dir))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_port

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{port}"

    server.shutdown()


def test_e2e_privacy_zero_external_traffic_and_csp(static_server: str, tmp_path: Path):
    """Valida que o site estático opera sem chamadas de rede externas e sob CSP rigorosa."""
    import qrcode

    # 1. Gera imagem sintética de teste com QRCode
    qr_img = qrcode.make("https://cartorio.exemplo.com.br/selo-digital/12345")
    sample_qr_path = tmp_path / "sample_qr.png"
    qr_img.save(str(sample_qr_path))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        requests_logged: List[dict] = []

        def on_request(req):
            requests_logged.append({
                "url": req.url,
                "method": req.method,
            })

        page.on("request", on_request)

        # 2. Navega para a página inicial
        response = page.goto(static_server, wait_until="networkidle")
        assert response is not None
        assert response.status == 200

        # Verifica presença dos headers de CSP
        headers = response.headers
        csp = headers.get("content-security-policy", "")
        assert "connect-src 'self'" in csp
        assert "default-src 'self'" in csp

        # 3. Testa bloqueio ativo de conexões externas pelo CSP
        csp_blocked = page.evaluate("""async () => {
            try {
                await fetch('https://httpbin.org/post', {
                    method: 'POST',
                    body: JSON.stringify({ secret: 'dado_vazado' }),
                });
                return false;
            } catch (err) {
                return true;
            }
        }""")
        assert csp_blocked, "O CSP deveria ter bloqueado ativamente a chamada fetch externa"

        # 4. Aguarda inicialização do motor offline
        page.wait_for_selector(".engine-bar.ready", timeout=25000)
        engine_text = page.locator("#engine-status-text").text_content()
        assert "Motor pronto" in engine_text

        # Limpa registro de requisições de inicialização de assets
        requests_during_validation: List[dict] = []
        page.on("request", lambda req: requests_during_validation.append({
            "url": req.url,
            "method": req.method,
        }))

        # 5. Envia documento via input file
        page.set_input_files("#file-input", str(sample_qr_path))

        # 6. Aguarda o resultado ser exibido
        page.wait_for_selector("#result-section", state="visible", timeout=15000)

        # 7. Garante que o selo de validação no navegador está visível
        privacy_badge = page.locator("#privacy-badge")
        assert privacy_badge.is_visible()
        assert "Processado no seu navegador · offline" in privacy_badge.text_content()

        # 8. Garantia de Privacidade: NENHUMA requisição POST e NENHUMA requisição externa
        for req in requests_during_validation:
            assert req["method"] != "POST", f"Requisição POST indevida detectada: {req}"
            assert req["url"].startswith(static_server), f"Tráfego externo indevido detectado: {req['url']}"

        # 9. Testa abertura e fechamento do modal de auditoria de privacidade
        btn_audit = page.locator("#btn-open-audit-modal")
        assert btn_audit.is_visible()
        btn_audit.click()

        modal_audit = page.locator("#modal-audit")
        page.wait_for_selector("#modal-audit", state="visible", timeout=2000)
        assert modal_audit.is_visible()

        btn_close_audit = page.locator("#btn-close-audit-modal")
        btn_close_audit.click()
        page.wait_for_selector("#modal-audit", state="hidden", timeout=2000)
        assert not modal_audit.is_visible()

        browser.close()


def test_e2e_pwa_and_offline_mode(static_server: str, tmp_path: Path):
    """Valida a instalação PWA e a execução completa com rede offline."""
    import qrcode

    qr_img = qrcode.make("https://cartorio.exemplo.com.br/selo-digital/offline-test")
    sample_qr_path = tmp_path / "sample_qr_offline.png"
    qr_img.save(str(sample_qr_path))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 1. Carrega a página e aguarda motor e Service Worker
        page.goto(static_server, wait_until="networkidle")
        page.wait_for_selector(".engine-bar.ready", timeout=25000)

        # 2. Verifica manifesto PWA
        manifest_link = page.locator('link[rel="manifest"]')
        assert manifest_link.count() > 0
        assert manifest_link.get_attribute("href") == "/manifest.json"

        # 3. Simula rede completamente offline
        context.set_offline(True)

        # 4. Inicia nova consulta em modo desconectado
        page.click("#btn-browse")  # Garante que controles continuam responsivos
        page.set_input_files("#file-input", str(sample_qr_path))

        # 5. Validação ocorre com sucesso mesmo offline
        page.wait_for_selector("#result-section", state="visible", timeout=15000)
        privacy_badge = page.locator("#privacy-badge")
        assert privacy_badge.is_visible()
        assert "Processado no seu navegador · offline" in privacy_badge.text_content()

        # Restaura conexão
        context.set_offline(False)
        browser.close()

from __future__ import annotations

import base64
import logging
import re
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from viodigital.core import DigitalDocumentChecker, present
from viodigital.core.__meta__ import __version__
from viodigital.core.exceptions import DigitalDocumentError, QRCodeNotFoundError

app = FastAPI(
    title="VioDigital API",
    description="Verificador e decodificador offline de CRLV-e, CNH, ATPV-e, CIN e +160 documentos oficiais Serpro/VIO",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; connect-src 'self'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval' blob:; worker-src 'self' blob:; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; font-src 'self'; manifest-src 'self';"
    )
    response.headers["Permissions-Policy"] = "camera=(self)"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"

    path = request.url.path
    if "Cache-Control" not in response.headers:
        if path.startswith("/static/vendor/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif path.startswith("/static/wheels/") or path in (
            "/static/app.js",
            "/static/scanner.worker.js",
            "/static/style.css",
            "/",
        ) or path.endswith(".html"):
            response.headers["Cache-Control"] = "no-cache"

    return response

MAX_UPLOAD_SIZE = 15 * 1024 * 1024  # 15 MB

logger = logging.getLogger("viodigital.api")
_checker = DigitalDocumentChecker()
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
SRC_WEB_DIR = Path(__file__).resolve().parent.parent / "web"
DIST_DIR = ROOT_DIR / "dist"
# Prioriza o código-fonte ao vivo em execução local para refletir alterações imediatamente
WEB_DIR = SRC_WEB_DIR if (SRC_WEB_DIR / "index.html").exists() else DIST_DIR

# Provisiona e atualiza os ativos de runtime do navegador (ex: wheel WASM atualizada)
try:
    from viodigital.build_static import ensure_runtime_assets
    ensure_runtime_assets(WEB_DIR)
except Exception as _e:
    logger.warning("Provisionamento de ativos de runtime do navegador adiado: %s", _e)

SEO_DOC_PAGES: Dict[str, Dict[str, str]] = {
    "crlv": {
        "title": "Validar QR Code CRLV-e Digital e CRV-e RENAVE no PC (Grátis) — VioDigital",
        "description": "Valide gratuitamente o QR Code VIO do CRLV-e Digital (Templates 10, 12, 62, 70) e CRV-e RENAVE (Template 24) no computador por PDF, Ctrl+V ou Webcam. Extração imediata de Placa, RENAVAM, Chassi e Proprietário.",
        "hero_title": "Validador Oficial de CRLV-e Digital e CRV-e RENAVE",
        "hero_subtitle": "Arraste o PDF do CRLV-e recebido no WhatsApp, cole um print (Ctrl+V) ou aponte o documento impresso para a webcam para validar a assinatura Serpro/SENATRAN e copiar Placa, RENAVAM, Chassi e CPF/CNPJ.",
    },
    "cnh": {
        "title": "Validar QR Code CNH Digital e Física no Computador (Com Foto 3x4) — VioDigital",
        "description": "Leia e valide gratuitamente o QR Code da CNH Digital e Física no PC (Templates VIO 2, 4 e 83). Verifica a assinatura digital SENATRAN e decodifica a fotografia biométrica BPG 3x4 do condutor.",
        "hero_title": "Validador de CNH Digital e Física (Com Fotografia Biométrica)",
        "hero_subtitle": "Confira a autenticidade da Carteira Nacional de Habilitação pelo computador, visualize a fotografia biométrica 3x4 assinada pelo Serpro e copie CPF, Registro, RENACH, Filiação e Validade em 1 clique.",
    },
    "atpv": {
        "title": "Validar QR Code ATPV-e (Intenção de Venda) para Cartório no PC — VioDigital",
        "description": "Valide gratuitamente a ATPV-e (Autorização para Transferência de Propriedade de Veículo — Template VIO 43) no computador. Extrai dados completos do Vendedor, Comprador, Valor da Venda, Hodômetro e CRV para reconhecimento de firma.",
        "hero_title": "Validador Notarial de ATPV-e (Intenção de Venda)",
        "hero_subtitle": "Conferência instantânea de ATPV-e para reconhecimento de firma em cartório: valida o QR Code VIO mesmo em páginas com Selo Digital do TJ e extrai Vendedor, Comprador, Placa, Chassi, Valor e Hodômetro.",
    },
    "cin": {
        "title": "Validar QR Code CIN / Novo RG Nacional (ICP-Brasil) no PC — VioDigital",
        "description": "Verifique gratuitamente o QR Code da Carteira de Identidade Nacional (CIN / Novo RG), RG Digital Estadual e DNI diretamente no computador com validação criptográfica ES512 ICP-Brasil.",
        "hero_title": "Validador de CIN (Carteira de Identidade Nacional / Novo RG)",
        "hero_subtitle": "Verifique a assinatura digital ICP-Brasil (ES512) do QR Code da nova Carteira de Identidade Nacional, RG Digital Estadual e DNI diretamente pelo navegador ou webcam.",
    },
    "tie-marinha": {
        "title": "Validar QR Code TIE (Título de Inscrição de Embarcação) e CHA da Marinha — VioDigital",
        "description": "Valide gratuitamente documentos náuticos da Marinha do Brasil (DPC) com QR Code VIO: TIE (Título de Inscrição de Embarcação PF e PJ — Templates 116 e 118) e CHA (Carteira de Habilitação de Amador e Motonauta).",
        "hero_title": "Validador de TIE (Embarcações) e CHA da Marinha do Brasil",
        "hero_subtitle": "Ideal para cartórios litorâneos e despachantes marítimos: valide a autenticidade do Título de Inscrição de Embarcação (TIE PF/PJ) e Carteira de Arrais/Motonauta (CHA) extraindo todos os 34 campos oficiais.",
    },
}


class VerifyBase64Request(BaseModel):
    data: str
    filename: Optional[str] = None


_format_result = present


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "VioDigital", "version": __version__}


@app.get("/api/version")
async def version_info():
    from viodigital.build_static import compute_engine_hash

    return JSONResponse(
        content={"version": __version__, "build_hash": compute_engine_hash()},
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.get("/sw.js")
async def service_worker():
    sw_file = WEB_DIR / "sw.js"
    if not sw_file.exists():
        raise HTTPException(status_code=404)
    from viodigital.build_static import compute_engine_hash

    content = sw_file.read_text(encoding="utf-8").replace("__BUILD_HASH__", compute_engine_hash())
    return Response(
        content=content,
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.get("/manifest.json")
async def pwa_manifest():
    manifest_file = WEB_DIR / "manifest.json"
    if not manifest_file.exists():
        raise HTTPException(status_code=404)
    return Response(
        content=manifest_file.read_text(encoding="utf-8"),
        media_type="application/manifest+json",
    )


@app.get("/api/templates")
async def list_supported_templates():
    templates_list = []
    store = getattr(_checker, "templates", None)
    by_id = getattr(store, "_by_id", {}) if store else {}
    for tpl_id in sorted(by_id.keys()):
        tpl = by_id[tpl_id]
        templates_list.append({
            "id": tpl.id,
            "name": tpl.name,
            "owner": tpl.owner,
            "fields_count": len(tpl.field_names),
        })

    return {
        "total_templates": len(templates_list),
        "cin_supported": True,
        "templates": templates_list,
        "categories": [
            {
                "id": "transito_senatran",
                "title": "Trânsito e Veículos (SENATRAN / DETRAN / PRF)",
                "documents": [
                    "CRLV-e Digital (Templates 10, 12, 62, 70)",
                    "CRV-e RENAVE (Template 24)",
                    "CNH Digital e Física com Foto Biométrica (Templates 2, 4, 83)",
                    "ATPV-e — Autorização para Transferência de Propriedade (Template 43)",
                    "Placa Veicular Mercosul (Templates 11, 17)",
                    "Credencial de Estacionamento Idoso/PcD (Templates 95, 162)",
                    "Boletim de Acidente de Trânsito PRF (Templates 50, 51)",
                    "Carteira de Instrutor de Trânsito (Template 237)",
                ],
            },
            {
                "id": "identificacao_civil",
                "title": "Identificação Civil Nacional",
                "documents": [
                    "CIN — Carteira de Identidade Nacional / Novo RG (JWT ICP-Brasil ES512)",
                    "RG Digital Estadual (Templates 91, 92)",
                    "DNI — Documento Nacional de Identidade (Templates 8, 9, 73)",
                    "CPF Digital (Template 25)",
                    "Carteira de Identidade Estudantil MEC (Templates 23, 236)",
                ],
            },
            {
                "id": "marinha_nautica",
                "title": "Marinha do Brasil / Embarcações (DPC)",
                "documents": [
                    "TIE — Título de Inscrição de Embarcação PF e PJ (Templates 116, 118)",
                    "CHA — Carteira de Habilitação de Amador e Motonauta (Templates 97, 104, 110)",
                    "Certificados Marítimos DPC-1031, DPC-1033 e DPC-1034 (Templates 141, 151, 167)",
                ],
            },
            {
                "id": "defesa_seguranca",
                "title": "Exército, Armas (SFPC) e Segurança Pública",
                "documents": [
                    "CRAF — Certificado de Registro de Arma de Fogo (Template 52)",
                    "Guia de Tráfego de Armas e Munições — Exército (Template 53)",
                    "Identidades Militares do Exército e Força Aérea Brasileira (Templates 79, 108)",
                    "Identidades Funcionais de Polícia, Bombeiros, PM e GCM (Templates 102, 107, 122, 128, 160, 183, 191)",
                ],
            },
            {
                "id": "conselhos_funcionais",
                "title": "Conselhos Profissionais, Judiciário, MP e Defensoria",
                "documents": [
                    "Carteiras Profissionais CREA (PR, RS, RN, SE, CE, TO, AL)",
                    "Carteiras Profissionais CRA (incluindo CRA-SC, CRA-SP, CRA-RS, CRA-PR, CRA-ES, CRA-BA)",
                    "Carteiras Profissionais CREF, CREFITO, CFN e CONFERP",
                    "Identidades Funcionais de Magistrados (TJ), Ministério Público (MP) e Defensoria Pública (DPE)",
                ],
            },
            {
                "id": "saude_trabalho_tesouro",
                "title": "Saúde, Trabalho e Administração Federal",
                "documents": [
                    "Atestado Médico Digital — Ministério da Saúde (Template 31)",
                    "CAT — Comunicação de Acidente de Trabalho (Template 229)",
                    "Extrato CAUC, Recibos SICONFI e Nota CAPAG (Tesouro Nacional)",
                ],
            },
        ],
    }


@app.api_route("/robots.txt", methods=["GET", "HEAD"])
async def robots_txt():
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/documents/\n\n"
        "Sitemap: https://viodigital.com.br/sitemap.xml\n"
    )
    return PlainTextResponse(content=content, status_code=200)


@app.api_route("/sitemap.xml", methods=["GET", "HEAD"])
async def sitemap_xml():
    urls = [
        ("https://viodigital.com.br/", "1.0"),
        ("https://viodigital.com.br/documentos", "0.9"),
        ("https://viodigital.com.br/privacidade", "0.9"),
        ("https://viodigital.com.br/validar-crlv", "0.9"),
        ("https://viodigital.com.br/validar-cnh", "0.9"),
        ("https://viodigital.com.br/validar-atpv", "0.9"),
        ("https://viodigital.com.br/validar-cin", "0.8"),
        ("https://viodigital.com.br/validar-tie-marinha", "0.8"),
        ("https://viodigital.com.br/apoiar", "0.7"),
    ]
    items = "\n".join(
        f"  <url>\n    <loc>{loc}</loc>\n    <changefreq>weekly</changefreq>\n    <priority>{prio}</priority>\n  </url>"
        for loc, prio in urls
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{items}\n"
        "</urlset>\n"
    )
    return Response(content=xml, media_type="application/xml", status_code=200)


@app.api_route("/llms.txt", methods=["GET", "HEAD"])
async def llms_txt():
    llms_file = WEB_DIR / "llms.txt"
    if llms_file.exists():
        content = llms_file.read_text(encoding="utf-8")
    else:
        content = (
            "# VioDigital\n\n"
            "> Verificador e decodificador offline de documentos oficiais brasileiros (CRLV-e, CNH, ATPV-e, CIN e +160 templates Serpro/VIO).\n\n"
            "## Links\n"
            "- Site: https://viodigital.com.br/\n"
            "- Documentos: https://viodigital.com.br/documentos\n"
            "- Privacidade (LGPD): https://viodigital.com.br/privacidade\n"
            "- Repositório: https://github.com/Kauerc10/VioDigital\n"
        )
    return PlainTextResponse(content=content, status_code=200)


@app.get("/404")
@app.get("/404.html")
async def not_found_page():
    html_404_file = WEB_DIR / "404.html"
    if html_404_file.exists():
        return HTMLResponse(content=html_404_file.read_text(encoding="utf-8"), status_code=404)
    return HTMLResponse(content="<h1>404 — Página Não Encontrada</h1>", status_code=404)


@app.exception_handler(404)
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=404, content={"error": "NOT_FOUND", "message": "Endpoint não encontrado."})
        html_404_file = WEB_DIR / "404.html"
        if html_404_file.exists():
            return HTMLResponse(content=html_404_file.read_text(encoding="utf-8"), status_code=404)
        return HTMLResponse(content="<h1>404 — Página Não Encontrada</h1><p><a href='/'>Ir para o início</a></p>", status_code=404)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


@app.post("/api/documents/verify")
async def verify_document(file: UploadFile = File(...)):
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Arquivo vazio.")

        if len(content) > MAX_UPLOAD_SIZE:
            return JSONResponse(
                status_code=413,
                content={
                    "is_parsed": False,
                    "error": "PAYLOAD_TOO_LARGE",
                    "message": f"Arquivo excede o tamanho máximo permitido de {MAX_UPLOAD_SIZE // (1024 * 1024)}MB.",
                },
            )

        result = _checker.parse_file(content)
        return JSONResponse(_format_result(result))
    except QRCodeNotFoundError as exc:
        return JSONResponse(
            status_code=422,
            content={
                "is_parsed": False,
                "error": "QR_NOT_FOUND",
                "message": str(exc),
            },
        )
    except DigitalDocumentError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "is_parsed": False,
                "error": "PARSE_ERROR",
                "message": str(exc),
            },
        )
    except Exception as exc:
        import logging

        logging.getLogger("viodigital.api").exception("Erro inesperado no processamento: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "is_parsed": False,
                "error": "SERVER_ERROR",
                "message": "Erro interno ao processar documento. Tente novamente mais tarde.",
            },
        )


@app.post("/api/documents/verify-base64")
async def verify_document_base64(req: VerifyBase64Request):
    try:
        data_str = req.data
        if "," in data_str:
            data_str = data_str.split(",", 1)[1]

        content = base64.b64decode(data_str)
        if len(content) > MAX_UPLOAD_SIZE:
            return JSONResponse(
                status_code=413,
                content={
                    "is_parsed": False,
                    "error": "PAYLOAD_TOO_LARGE",
                    "message": f"Arquivo excede o tamanho máximo permitido de {MAX_UPLOAD_SIZE // (1024 * 1024)}MB.",
                },
            )

        result = _checker.parse_file(content)
        return JSONResponse(_format_result(result))
    except QRCodeNotFoundError as exc:
        return JSONResponse(
            status_code=422,
            content={
                "is_parsed": False,
                "error": "QR_NOT_FOUND",
                "message": str(exc),
            },
        )
    except Exception as exc:
        import logging

        logging.getLogger("viodigital.api").exception("Erro inesperado no processamento base64: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "is_parsed": False,
                "error": "PROCESSING_ERROR",
                "message": "Erro interno ao processar documento. Tente novamente mais tarde.",
            },
        )


# Servir frontend estático e páginas dedicadas
if (WEB_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")


@app.get("/")
async def root():
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "VioDigital API operacional. Frontend não localizado."}


@app.get("/documentos")
async def page_documentos():
    page = WEB_DIR / "documentos.html"
    if page.exists():
        return FileResponse(page)
    raise HTTPException(status_code=404)


@app.get("/apoiar")
async def page_apoiar():
    page = WEB_DIR / "apoiar.html"
    if page.exists():
        return FileResponse(page)
    raise HTTPException(status_code=404)


@app.get("/privacidade")
async def page_privacidade():
    for base in (WEB_DIR, SRC_WEB_DIR):
        page = base / "privacidade.html"
        if page.exists():
            return FileResponse(page)
    raise HTTPException(status_code=404)


@app.get("/validar-{slug}")
async def page_validar_documento(slug: str):
    meta = SEO_DOC_PAGES.get(slug)
    if not meta:
        raise HTTPException(status_code=404, detail="Página de documento não encontrada.")
    index_file = WEB_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404)

    html = index_file.read_text(encoding="utf-8")
    canonical_url = f"https://viodigital.com.br/validar-{slug}"
    html = re.sub(r"<title>.*?</title>", f"<title>{meta['title']}</title>", html, flags=re.DOTALL)
    html = re.sub(
        r'<meta name="description" content=".*?">',
        f'<meta name="description" content="{meta["description"]}">',
        html,
    )
    html = re.sub(
        r'<link rel="canonical" href=".*?">',
        f'<link rel="canonical" href="{canonical_url}">',
        html,
    )
    html = re.sub(
        r'<meta property="og:title" content=".*?">',
        f'<meta property="og:title" content="{meta["title"]}">',
        html,
    )
    html = re.sub(
        r'<meta property="og:description" content=".*?">',
        f'<meta property="og:description" content="{meta["description"]}">',
        html,
    )
    html = re.sub(
        r'<meta property="og:url" content=".*?">',
        f'<meta property="og:url" content="{canonical_url}">',
        html,
    )
    html = html.replace(
        '<h2 id="hero-title">Validação de Documentos Oficiais</h2>',
        f'<h2 id="hero-title">{meta["hero_title"]}</h2>',
    )
    html = re.sub(
        r'<p class="dropzone-hint" id="hero-subtitle">.*?</p>',
        f'<p class="dropzone-hint" id="hero-subtitle">{meta["hero_subtitle"]}</p>',
        html,
    )
    return HTMLResponse(content=html, status_code=200)

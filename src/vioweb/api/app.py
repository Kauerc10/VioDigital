from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from vioweb.core import DigitalDocumentChecker
from vioweb.core.documents.atpv import ATPVData
from vioweb.core.documents.crlv import CRLVData
from vioweb.core.documents.cnh import CNHData
from vioweb.core.exceptions import DigitalDocumentError, QRCodeNotFoundError

app = FastAPI(
    title="VioWeb API",
    description="Verificador e decodificador offline de CRLV-e, CNH, ATPV-e, CIN e +160 documentos oficiais Serpro/VIO",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_checker = DigitalDocumentChecker()
WEB_DIR = Path(__file__).parent.parent / "web"

SEO_DOC_PAGES: Dict[str, Dict[str, str]] = {
    "crlv": {
        "title": "Validar QR Code CRLV-e Digital e CRV-e RENAVE no PC (Grátis) — VioWeb",
        "description": "Valide gratuitamente o QR Code VIO do CRLV-e Digital (Templates 10, 12, 62, 70) e CRV-e RENAVE (Template 24) no computador por PDF, Ctrl+V ou Webcam. Extração imediata de Placa, RENAVAM, Chassi e Proprietário.",
        "hero_title": "Validador Oficial de CRLV-e Digital e CRV-e RENAVE",
        "hero_subtitle": "Arraste o PDF do CRLV-e recebido no WhatsApp, cole um print (Ctrl+V) ou aponte o documento impresso para a webcam para validar a assinatura Serpro/SENATRAN e copiar Placa, RENAVAM, Chassi e CPF/CNPJ.",
    },
    "cnh": {
        "title": "Validar QR Code CNH Digital e Física no Computador (Com Foto 3x4) — VioWeb",
        "description": "Leia e valide gratuitamente o QR Code da CNH Digital e Física no PC (Templates VIO 2, 4 e 83). Verifica a assinatura digital SENATRAN e decodifica a fotografia biométrica BPG 3x4 do condutor.",
        "hero_title": "Validador de CNH Digital e Física (Com Fotografia Biométrica)",
        "hero_subtitle": "Confira a autenticidade da Carteira Nacional de Habilitação pelo computador, visualize a fotografia biométrica 3x4 assinada pelo Serpro e copie CPF, Registro, RENACH, Filiação e Validade em 1 clique.",
    },
    "atpv": {
        "title": "Validar QR Code ATPV-e (Intenção de Venda) para Cartório no PC — VioWeb",
        "description": "Valide gratuitamente a ATPV-e (Autorização para Transferência de Propriedade de Veículo — Template VIO 43) no computador. Extrai dados completos do Vendedor, Comprador, Valor da Venda, Hodômetro e CRV para reconhecimento de firma.",
        "hero_title": "Validador Notarial de ATPV-e (Intenção de Venda)",
        "hero_subtitle": "Conferência instantânea de ATPV-e para reconhecimento de firma em cartório: valida o QR Code VIO mesmo em páginas com Selo Digital do TJ e extrai Vendedor, Comprador, Placa, Chassi, Valor e Hodômetro.",
    },
    "cin": {
        "title": "Validar QR Code CIN / Novo RG Nacional (ICP-Brasil) no PC — VioWeb",
        "description": "Verifique gratuitamente o QR Code da Carteira de Identidade Nacional (CIN / Novo RG), RG Digital Estadual e DNI diretamente no computador com validação criptográfica ES512 ICP-Brasil.",
        "hero_title": "Validador de CIN (Carteira de Identidade Nacional / Novo RG)",
        "hero_subtitle": "Verifique a assinatura digital ICP-Brasil (ES512) do QR Code da nova Carteira de Identidade Nacional, RG Digital Estadual e DNI diretamente pelo navegador ou webcam.",
    },
    "tie-marinha": {
        "title": "Validar QR Code TIE (Título de Inscrição de Embarcação) e CHA da Marinha — VioWeb",
        "description": "Valide gratuitamente documentos náuticos da Marinha do Brasil (DPC) com QR Code VIO: TIE (Título de Inscrição de Embarcação PF e PJ — Templates 116 e 118) e CHA (Carteira de Habilitação de Amador e Motonauta).",
        "hero_title": "Validador de TIE (Embarcações) e CHA da Marinha do Brasil",
        "hero_subtitle": "Ideal para cartórios litorâneos e despachantes marítimos: valide a autenticidade do Título de Inscrição de Embarcação (TIE PF/PJ) e Carteira de Arrais/Motonauta (CHA) extraindo todos os 34 campos oficiais.",
    },
}


class VerifyBase64Request(BaseModel):
    data: str
    filename: Optional[str] = None


def _mask_cpf_cnpj(val: str) -> str:
    digits = re.sub(r"\D", "", val or "")
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    if len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    return val


def _format_generic_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in fields.items():
        if not isinstance(v, str) or not v.strip():
            out[k] = v
            continue
        key_lower = k.lower()
        val_clean = v.strip()
        if any(tok in key_lower for tok in ("cpf", "cnpj", "documento_proprietario", "documento_vendedor", "documento_comprador")):
            out[k] = _mask_cpf_cnpj(val_clean)
        elif "placa" in key_lower and len(re.sub(r"[^A-Za-z0-9]", "", val_clean)) == 7:
            out[k] = re.sub(r"[^A-Za-z0-9]", "", val_clean).upper()
        elif "renavam" in key_lower and re.sub(r"\D", "", val_clean):
            digits = re.sub(r"\D", "", val_clean)
            out[k] = digits.zfill(11) if len(digits) <= 11 else val_clean
        else:
            out[k] = val_clean
    return out


def _format_result(res) -> Dict[str, Any]:
    formatted: Dict[str, Any] = {}
    data_obj = res.data

    if isinstance(data_obj, CRLVData):
        formatted = {
            "placa_formatada": data_obj.placa_formatada,
            "cpf_cnpj_formatado": data_obj.cpf_cnpj_formatado,
            "renavam_formatado": data_obj.renavam_formatado,
            "ano_fabricacao_modelo": data_obj.ano_fabricacao_modelo,
            "proprietario": data_obj.proprietario,
            "chassi": data_obj.chassi,
            "marca_modelo": data_obj.marca_modelo,
            "exercicio": data_obj.exercicio,
            "uf": data_obj.uf,
            "municipio": data_obj.local,
            "combustivel": data_obj.combustivel,
            "cor": data_obj.cor,
            "categoria": data_obj.categoria,
            "especie": data_obj.especie,
            "tipo": data_obj.tipo,
            "carroceria": data_obj.carroceria,
            "potencia": data_obj.potencia,
            "cilindradas": data_obj.cilindradas,
            "motor": data_obj.motor,
            "capacidade_maxima_carga": data_obj.capacidade_maxima_carga,
            "pbt": data_obj.pbt,
            "cmt": data_obj.cmt,
            "lotacao": data_obj.lotacao,
            "eixos": data_obj.eixos,
            "rntrc": data_obj.rntrc,
            "codigo_seguranca_cla": data_obj.codigo_seguranca_cla,
            "numero_crv": data_obj.numero_crv,
            "data_emissao": data_obj.data,
            "observacoes": data_obj.observacoes,
        }
    elif isinstance(data_obj, CNHData):
        formatted = {
            "nome": data_obj.nome,
            "nome_civil": data_obj.nome_civil,
            "cpf_formatado": data_obj.cpf_formatado,
            "identidade": data_obj.identidade,
            "data_nascimento": data_obj.data_nascimento,
            "filiacao_mae": data_obj.filiacao_mae,
            "filiacao_pai": data_obj.filiacao_pai,
            "categoria": data_obj.categoria,
            "numero_registro": data_obj.numero_registro,
            "data_validade": data_obj.data_validade,
            "data_primeira_habilitacao": data_obj.data_primeira_habilitacao,
            "data_emissao": data_obj.data_emissao,
            "local_emissao": data_obj.local_emissao,
            "uf_emissao": data_obj.uf_emissao,
            "numero_renach": data_obj.numero_renach,
            "numero_validacao_cnh": data_obj.numero_validacao_cnh,
            "permissao": data_obj.permissao,
            "acc": data_obj.acc,
            "observacoes": data_obj.observacoes,
        }
    elif isinstance(data_obj, ATPVData):
        formatted = {
            "numero_atpv": data_obj.numero_atpv,
            "placa_formatada": data_obj.placa_formatada,
            "renavam_formatado": data_obj.renavam_formatado,
            "chassi": data_obj.chassi,
            "valor_venda": data_obj.valor_venda,
            "local_venda": data_obj.local_venda,
            "data_venda": data_obj.data_venda,
            "numero_crv": data_obj.numero_crv,
            "codigo_seguranca_crv": data_obj.codigo_seguranca_crv,
            "uf_emissao_crv": data_obj.uf_emissao_crv,
            "data_emissao_crv": data_obj.data_emissao_crv,
            "marca_modelo": data_obj.marca_modelo,
            "cor": data_obj.cor,
            "ano_fabricacao_modelo": data_obj.ano_fabricacao_modelo,
            "kilometragem_hodometro": data_obj.kilometragem_hodometro,
            "nome_vendedor": data_obj.nome_vendedor,
            "documento_vendedor_formatado": data_obj.documento_vendedor_formatado,
            "email_vendedor": data_obj.email_vendedor,
            "municipio_vendedor": data_obj.municipio_vendedor,
            "uf_vendedor": data_obj.uf_vendedor,
            "nome_comprador": data_obj.nome_comprador,
            "documento_comprador_formatado": data_obj.documento_comprador_formatado,
            "email_comprador": data_obj.email_comprador,
            "municipio_comprador": data_obj.municipio_comprador,
            "uf_comprador": data_obj.uf_comprador,
        }
    elif isinstance(res.fields, dict) and res.fields:
        formatted = _format_generic_fields(res.fields)

    photo_b64 = None
    photo_obj = getattr(res, "photo", None)
    if photo_obj and getattr(photo_obj, "data", None):
        try:
            try:
                png_bytes = photo_obj.to_png()
                photo_b64 = f"data:image/png;base64,{base64.b64encode(png_bytes).decode('ascii')}"
            except Exception:
                fmt = (getattr(photo_obj, "format", None) or "jpeg").lower()
                photo_b64 = f"data:image/{fmt};base64,{base64.b64encode(photo_obj.data).decode('ascii')}"
        except Exception:
            photo_b64 = None

    message = None
    if not res.is_parsed:
        if res.errors:
            message = "Falha ao decodificar documento: " + "; ".join(res.errors)
        else:
            message = "Não foi possível decodificar o envelope VIO deste QR Code."
    elif res.warnings:
        message = "; ".join(res.warnings)

    return {
        "is_parsed": bool(res.is_parsed),
        "is_authentic": bool(res.is_authentic),
        "is_valid": bool(res.is_valid),
        "is_expired": bool(res.is_expired),
        "document_type": res.document_type,
        "document_name": res.document_name,
        "template_id": res.template_id,
        "template_name": res.template_name,
        "issued_at": res.issued_at.isoformat() if res.issued_at else None,
        "signature_algorithm": res.signature.algorithm if res.signature else None,
        "fields": res.fields,
        "formatted": formatted,
        "photo_b64": photo_b64,
        "photo_format": photo_obj.format if photo_obj else None,
        "errors": res.errors,
        "warnings": res.warnings,
        "message": message,
    }


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "VioWeb", "version": "0.1.0"}


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
        "total_templates": max(len(templates_list), 161),
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


@app.get("/robots.txt")
async def robots_txt():
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/documents/\n\n"
        "Sitemap: https://vioweb.vercel.app/sitemap.xml\n"
    )
    return PlainTextResponse(content=content, status_code=200)


@app.get("/sitemap.xml")
async def sitemap_xml():
    urls = [
        ("https://vioweb.vercel.app/", "1.0"),
        ("https://vioweb.vercel.app/documentos", "0.9"),
        ("https://vioweb.vercel.app/validar-crlv", "0.9"),
        ("https://vioweb.vercel.app/validar-cnh", "0.9"),
        ("https://vioweb.vercel.app/validar-atpv", "0.9"),
        ("https://vioweb.vercel.app/validar-cin", "0.8"),
        ("https://vioweb.vercel.app/validar-tie-marinha", "0.8"),
        ("https://vioweb.vercel.app/api-comercial", "0.8"),
        ("https://vioweb.vercel.app/apoiar", "0.7"),
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


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


@app.post("/api/documents/verify")
async def verify_document(file: UploadFile = File(...)):
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Arquivo vazio.")

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
        return JSONResponse(
            status_code=500,
            content={
                "is_parsed": False,
                "error": "SERVER_ERROR",
                "message": f"Erro inesperado no processamento: {exc}",
            },
        )


@app.post("/api/documents/verify-base64")
async def verify_document_base64(req: VerifyBase64Request):
    try:
        data_str = req.data
        if "," in data_str:
            data_str = data_str.split(",", 1)[1]

        content = base64.b64decode(data_str)
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
        return JSONResponse(
            status_code=400,
            content={
                "is_parsed": False,
                "error": "PROCESSING_ERROR",
                "message": str(exc),
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
    return {"message": "VioWeb API operacional. Frontend não localizado."}


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


@app.get("/api-comercial")
async def page_api_comercial():
    page = WEB_DIR / "api.html"
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
    canonical_url = f"https://vioweb.vercel.app/validar-{slug}"
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

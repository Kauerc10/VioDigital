from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from vioweb.core import DigitalDocumentChecker
from vioweb.core.documents.atpv import ATPVData
from vioweb.core.documents.crlv import CRLVData
from vioweb.core.documents.cnh import CNHData
from vioweb.core.exceptions import DigitalDocumentError, QRCodeNotFoundError

app = FastAPI(
    title="VioWeb API",
    description="Verificador e decodificador offline de CRLV-e e CNH Serpro/VIO",
    version="0.1.0",
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


class VerifyBase64Request(BaseModel):
    data: str
    filename: Optional[str] = None


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
        formatted = dict(res.fields)

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


@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(status_code=204, content=None)


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
            # remove data URL prefix like data:image/png;base64,
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


# Servir frontend estático
if (WEB_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")


@app.get("/")
async def root():
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "VioWeb API operacional. Frontend não localizado."}

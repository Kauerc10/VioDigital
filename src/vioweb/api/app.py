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
            "tipo": data_obj.tipo,
            "motor": data_obj.motor,
        }
    elif isinstance(data_obj, CNHData):
        formatted = {
            "nome": data_obj.nome,
            "cpf_formatado": data_obj.cpf_formatado,
            "categoria": data_obj.categoria,
            "numero_registro": data_obj.numero_registro,
            "data_validade": data_obj.data_validade,
            "data_emissao": data_obj.data_emissao,
            "local_emissao": data_obj.local_emissao,
            "uf_emissao": data_obj.uf_emissao,
            "numero_renach": data_obj.numero_renach,
        }

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
        "errors": res.errors,
        "warnings": res.warnings,
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

"""Módulo de apresentação compartilhado: formatação de campos e contrato JSON.

Define a função pura ``present(result)`` utilizada tanto pela API FastAPI
quanto pelo Web Worker no navegador (via Pyodide) para produzir uma estrutura
JSON idêntica e consistente.
"""

from __future__ import annotations

import base64
import re
from typing import Any, Dict

from .documents.atpv import ATPVData
from .documents.cin import CINData
from .documents.cnh import CNHData
from .documents.crlv import CRLVData
from .documents.dni import DNIData
from .documents.rg import RGData
from .models import DocumentResult


def mask_cpf_cnpj(val: str) -> str:
    """Aplica máscara de CPF (11 dígitos) ou CNPJ (14 dígitos) quando aplicável."""
    digits = re.sub(r"\D", "", val or "")
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    if len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    return val


def format_generic_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Aplica máscaras padrão (CPF, CNPJ, Placa, Renavam) em campos genéricos."""
    out: Dict[str, Any] = {}
    for k, v in fields.items():
        if not isinstance(v, str) or not v.strip():
            out[k] = v
            continue
        key_lower = k.lower()
        val_clean = v.strip()
        if any(
            tok in key_lower
            for tok in (
                "cpf",
                "cnpj",
                "documento_proprietario",
                "documento_vendedor",
                "documento_comprador",
            )
        ):
            out[k] = mask_cpf_cnpj(val_clean)
        elif "placa" in key_lower and len(re.sub(r"[^A-Za-z0-9]", "", val_clean)) == 7:
            out[k] = re.sub(r"[^A-Za-z0-9]", "", val_clean).upper()
        elif "renavam" in key_lower and re.sub(r"\D", "", val_clean):
            digits = re.sub(r"\D", "", val_clean)
            out[k] = digits.zfill(11) if len(digits) <= 11 else val_clean
        else:
            out[k] = val_clean
    return out


def present(res: DocumentResult) -> Dict[str, Any]:
    """Produz a representação em dicionário/JSON oficial do resultado da validação."""
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
            "placa_anterior_uf": data_obj.placa_anterior_uf,
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
    elif isinstance(data_obj, CINData):
        formatted = {
            "cpf_formatado": data_obj.cpf_formatado,
            "cpf": data_obj.cpf,
            "data_nascimento": data_obj.data_nascimento,
            "data_validade": data_obj.data_validade,
            "orgao_emissor": data_obj.iss,
            "uuid": data_obj.uuid,
            "url_validacao": data_obj.url,
            **{k: v for k, v in data_obj.outras_claims.items()},
        }
    elif isinstance(data_obj, DNIData):
        formatted = {
            "nome": data_obj.nome,
            "cpf_formatado": data_obj.cpf_formatado,
            "cpf": data_obj.cpf,
            "numero_icn": data_obj.numero_icn,
            "data_nascimento": data_obj.data_nascimento,
            "matricula_nascimento": data_obj.matricula_nascimento,
            "naturalidade": data_obj.naturalidade,
            "uf": data_obj.uf,
            "filiacao_1": data_obj.filiacao_1,
            "filiacao_2": data_obj.filiacao_2,
            "titulo_eleitor": data_obj.titulo_eleitor,
            "orgao_expedidor": data_obj.orgao_expedidor,
            "data_expedicao": data_obj.data_expedicao,
            "situacao_registro": data_obj.situacao_registro,
            "data_ultima_atualizacao": data_obj.data_ultima_atualizacao,
        }
    elif isinstance(data_obj, RGData):
        formatted = {
            "nome": data_obj.nome,
            "nome_social": data_obj.nome_social,
            "cpf_formatado": data_obj.cpf_formatado,
            "cpf": data_obj.cpf,
            "sexo": data_obj.sexo,
            "data_nascimento": data_obj.data_nascimento,
            "nacionalidade": data_obj.nacionalidade,
            "naturalidade": data_obj.naturalidade,
            "data_validade": data_obj.data_validade,
            "filiacao_1": data_obj.filiacao_1,
            "filiacao_2": data_obj.filiacao_2,
            "orgao_expedidor": data_obj.orgao_expedidor,
            "local_emissao": data_obj.local_emissao,
            "data_emissao": data_obj.data_emissao,
            "certidao": data_obj.certidao,
        }
    elif isinstance(res.fields, dict) and res.fields:
        formatted = format_generic_fields(res.fields)

    photo_b64 = None
    photo_obj = getattr(res, "photo", None)
    if photo_obj and getattr(photo_obj, "data", None):
        fmt = (getattr(photo_obj, "format", None) or "jpeg").lower()
        if fmt == "bpg":
            # Entrega direta para decodificação WebAssembly no navegador
            photo_b64 = f"data:image/bpg;base64,{base64.b64encode(photo_obj.data).decode('ascii')}"
        else:
            try:
                png_bytes = photo_obj.to_png()
                photo_b64 = f"data:image/png;base64,{base64.b64encode(png_bytes).decode('ascii')}"
            except Exception:
                photo_b64 = f"data:image/{fmt};base64,{base64.b64encode(photo_obj.data).decode('ascii')}"

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

from __future__ import annotations

import base64
from datetime import datetime, timezone

from vioweb.core.documents.atpv import ATPVData
from vioweb.core.documents.cnh import CNHData
from vioweb.core.documents.crlv import CRLVData
from vioweb.core.models import DocumentResult, Photo, SignatureInfo
from vioweb.core.presentation import format_generic_fields, mask_cpf_cnpj, present


def test_mask_cpf_cnpj():
    assert mask_cpf_cnpj("12345678901") == "123.456.789-01"
    assert mask_cpf_cnpj("12345678000195") == "12.345.678/0001-95"
    assert mask_cpf_cnpj("123") == "123"


def test_format_generic_fields():
    raw = {
        "cpf_proprietario": "12345678901",
        "cnpj_empresa": "12345678000195",
        "placa_veiculo": "abc1d23",
        "renavam_code": "123456",
        "outra_informacao": "texto normal",
    }
    fmt = format_generic_fields(raw)
    assert fmt["cpf_proprietario"] == "123.456.789-01"
    assert fmt["cnpj_empresa"] == "12.345.678/0001-95"
    assert fmt["placa_veiculo"] == "ABC1D23"
    assert fmt["renavam_code"] == "00000123456"
    assert fmt["outra_informacao"] == "texto normal"


def test_present_crlv():
    res = DocumentResult(raw=b"test_raw")
    res.is_parsed = True
    res.is_authentic = True
    res.is_valid = True
    res.document_type = "crlv"
    res.document_name = "CRLV Digital"
    res.template_id = 70
    res.template_name = "CRLV Digital"
    res.signature = SignatureInfo(algorithm="SHA256withRSA")
    res.issued_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    fields = {
        "placa": "ABC1D23",
        "cpf_cnpj": "12345678901",
        "renavam": "12345678901",
        "chassi": "9BWZZZ377VT004251",
        "nome": "JOAO DA SILVA",
        "marca_modelo": "VW/GOL",
        "exercicio": "2026",
    }
    res.fields = fields
    res.data = CRLVData(**fields)

    dto = present(res)
    assert dto["is_parsed"] is True
    assert dto["is_authentic"] is True
    assert dto["document_type"] == "crlv"
    assert dto["formatted"]["placa_formatada"] == "ABC1D23"
    assert dto["formatted"]["cpf_cnpj_formatado"] == "123.456.789-01"
    assert dto["formatted"]["renavam_formatado"] == "12345678901"
    assert dto["signature_algorithm"] == "SHA256withRSA"


def test_present_cnh_with_bpg_photo():
    res = DocumentResult(raw=b"test_raw")
    res.is_parsed = True
    res.is_authentic = True
    res.is_valid = True
    res.document_type = "cnh"
    res.document_name = "CNH Digital"
    res.template_id = 83

    fields = {
        "nome": "MARIA CONDUTORA",
        "cpf": "98765432100",
        "numero_registro": "01234567890",
        "categoria": "AB",
    }
    res.fields = fields
    res.data = CNHData(**fields)

    fake_bpg_bytes = b"BPG\x00fake_bytes_data"
    res.photo = Photo(data=fake_bpg_bytes, format="BPG")

    dto = present(res)
    assert dto["is_parsed"] is True
    assert dto["document_type"] == "cnh"
    assert dto["formatted"]["cpf_formatado"] == "987.654.321-00"
    assert dto["photo_format"] == "BPG"
    assert dto["photo_b64"].startswith("data:image/bpg;base64,")
    b64_part = dto["photo_b64"].split(",", 1)[1]
    assert base64.b64decode(b64_part) == fake_bpg_bytes


def test_present_atpv():
    res = DocumentResult(raw=b"test_raw")
    res.is_parsed = True
    res.is_authentic = True
    res.is_valid = True
    res.document_type = "atpv"
    res.document_name = "ATPV-e"
    res.template_id = 43

    fields = {
        "numero_atpv": "00012345678",
        "placa": "XYZ9K88",
        "renavam": "98765432100",
        "nome_vendedor": "CARLOS VENDEDOR",
        "documento_vendedor": "11122233344",
        "nome_comprador": "ANA COMPRADORA",
        "documento_comprador": "55566677788",
        "valor_venda": "R$ 50.000,00",
    }
    res.fields = fields
    res.data = ATPVData(**fields)

    dto = present(res)
    assert dto["is_parsed"] is True
    assert dto["document_type"] == "atpv"
    assert dto["formatted"]["placa_formatada"] == "XYZ9K88"
    assert dto["formatted"]["documento_vendedor_formatado"] == "111.222.333-44"
    assert dto["formatted"]["documento_comprador_formatado"] == "555.666.777-88"


def test_present_unparsed_with_errors():
    res = DocumentResult(raw=b"corrupt_data")
    res.is_parsed = False
    res.is_authentic = False
    res.is_valid = False
    res.add_error("Assinatura inválida")

    dto = present(res)
    assert dto["is_parsed"] is False
    assert dto["is_authentic"] is False
    assert "Assinatura inválida" in dto["message"]
    assert "Assinatura inválida" in dto["errors"]

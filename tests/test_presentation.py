from __future__ import annotations

import base64
from datetime import datetime, timezone

from viodigital.core.documents.atpv import ATPVData
from viodigital.core.documents.cin import CINData
from viodigital.core.documents.cnh import CNHData
from viodigital.core.documents.crlv import CRLVData
from viodigital.core.documents.dni import DNIData
from viodigital.core.documents.rg import RGData
from viodigital.core.models import DocumentResult, Photo, SignatureInfo
from viodigital.core.presentation import format_generic_fields, mask_cpf_cnpj, present


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


def test_present_cin():
    res = DocumentResult(raw=b"test_cin_jwt")
    res.is_parsed = True
    res.is_authentic = True
    res.is_valid = True
    res.document_type = "cin"
    res.document_name = "Carteira de Identidade Nacional"

    cin_data = CINData(
        iss="MJSP",
        cpf="11122233344",
        data_nascimento="15/08/1992",
        data_validade="15/08/2032",
        url="https://validar.iti.gov.br/c5d1e2f3-1234-5678-9abc-def012345678",
        uuid="c5d1e2f3-1234-5678-9abc-def012345678",
    )
    res.data = cin_data
    res.fields = cin_data.fields

    dto = present(res)
    assert dto["is_parsed"] is True
    assert dto["document_type"] == "cin"
    assert dto["formatted"]["cpf_formatado"] == "111.222.333-44"
    assert dto["formatted"]["data_nascimento"] == "15/08/1992"
    assert dto["formatted"]["orgao_emissor"] == "MJSP"
    assert dto["formatted"]["uuid"] == "c5d1e2f3-1234-5678-9abc-def012345678"


def test_present_dni_with_photo():
    res = DocumentResult(raw=b"test_dni_raw")
    res.is_parsed = True
    res.is_authentic = True
    res.is_valid = True
    res.document_type = "dni"
    res.document_name = "Documento Nacional de Identificação"
    res.template_id = 73

    dni_data = DNIData(
        numero_icn="123456789012345",
        nome="LUCAS ELEITOR",
        cpf="00100200304",
        data_nascimento="10/10/1995",
        naturalidade="SAO PAULO",
        uf="SP",
        titulo_eleitor="123456780123",
        orgao_expedidor="TSE",
    )
    res.data = dni_data
    res.fields = dni_data.fields
    res.photo = Photo(data=b"BPG\xfbphoto_dni", format="BPG")

    dto = present(res)
    assert dto["is_parsed"] is True
    assert dto["document_type"] == "dni"
    assert dto["formatted"]["cpf_formatado"] == "001.002.003-04"
    assert dto["formatted"]["nome"] == "LUCAS ELEITOR"
    assert dto["formatted"]["numero_icn"] == "123456789012345"
    assert dto["photo_format"] == "BPG"
    assert dto["photo_b64"].startswith("data:image/bpg;base64,")


def test_present_rg_digital():
    res = DocumentResult(raw=b"test_rg_raw")
    res.is_parsed = True
    res.is_authentic = True
    res.is_valid = True
    res.document_type = "rg"
    res.document_name = "RG Digital"
    res.template_id = 91

    rg_data = RGData(
        nome="FERNANDA SILVA",
        nome_social="FERNANDA SOCIAL",
        cpf="55544433322",
        data_nascimento="20/05/1990",
        sexo="F",
        nacionalidade="BRASILEIRA",
        naturalidade="CURITIBA",
        orgao_expedidor="SESP/PR",
    )
    res.data = rg_data
    res.fields = rg_data.fields
    res.photo = Photo(data=b"fake_jpeg", format="JPEG")

    dto = present(res)
    assert dto["is_parsed"] is True
    assert dto["document_type"] == "rg"
    assert dto["formatted"]["cpf_formatado"] == "555.444.333-22"
    assert dto["formatted"]["nome"] == "FERNANDA SILVA"
    assert dto["photo_format"] == "JPEG"
    assert dto["photo_b64"].startswith("data:image/jpeg;base64,")

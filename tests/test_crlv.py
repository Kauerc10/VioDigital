from datetime import datetime, timezone

from vioweb.core import DigitalDocumentChecker
from vioweb.core.documents.crlv import CRLVData, CRLVHandler
from tests.conftest import build_multiblock_qr

# Vetor com campos do CRLV Digital (Template 70)
CRLV_FIELDS = "^".join(
    [
        "12345678901",       # codigo_seguranca_cla
        "987654321",         # numero_crv
        "SP",                # uf
        "11223344556",       # renavam
        "",                  # rntrc
        "2026",              # exercicio
        "JOAO DA SILVA SAO PAULO", # nome
        "12345678909",       # cpf_cnpj
        "ABC1D23",           # placa
        "9BWZZZ377VT004251", # chassi
        "PASSAGEIRO",        # especie
        "AUTOMOVEL",         # tipo
        "FECHADA",           # carroceria
        "FLEX",              # combustivel
        "2023",              # ano_fabricacao
        "2024",              # ano_modelo
        "VW/GOL 1.0",        # marca_modelo
        "5",                 # lotacao
        "82",                # potencia
        "999",               # cilindradas
        "PARTICULAR",        # categoria
        "BRANCA",            # cor
        "CSE123456",         # motor
        "0.40",              # capacidade_maxima_carga
        "1.35",              # pbt
        "1.35",              # cmt
        "2",                 # eixos
        "SAO PAULO",         # local
        "15/01/2026",        # data
        "SEM RESTRICOES",    # observacoes
    ]
)

TIMESTAMP = 0x65A00000


def test_crlv_handler_matching():
    handler = CRLVHandler()
    assert handler.matches(10, None)
    assert handler.matches(12, None)
    assert handler.matches(62, None)
    assert handler.matches(70, None)
    assert not handler.matches(4, None)
    assert not handler.matches(83, None)


def test_crlv_data_formatting():
    data = CRLVData(
        placa="abc1d23",
        cpf_cnpj="12345678909",
        renavam="11223344556",
        ano_fabricacao="2023",
        ano_modelo="2024",
        nome="MARIA TESTE",
    )
    assert data.placa_formatada == "ABC1D23"
    assert data.cpf_cnpj_formatado == "123.456.789-09"
    assert data.renavam_formatado == "11223344556"
    assert data.ano_fabricacao_modelo == "2023/2024"
    assert data.proprietario == "MARIA TESTE"

    # Teste de CNPJ
    cnpj_data = CRLVData(cpf_cnpj="12345678000195")
    assert cnpj_data.cpf_cnpj_formatado == "12.345.678/0001-95"

    # Teste de Placa antiga (3 letras, 4 números)
    antiga_data = CRLVData(placa="abc1234")
    assert antiga_data.placa_formatada == "ABC-1234"


def test_crlv_parse_and_authenticate_v4(rsa_material, cert_store, crlv_template_store):
    qr = build_multiblock_qr(
        CRLV_FIELDS,
        version=4,
        template_id=70,
        timestamp=TIMESTAMP,
        sign=rsa_material["sign"],
    )

    checker = DigitalDocumentChecker(certificates=cert_store, templates=crlv_template_store)
    result = checker.parse_bytes(qr, now=datetime(2026, 2, 1, tzinfo=timezone.utc))

    assert result.is_parsed
    assert result.document_type == "crlv"
    assert result.template_id == 70
    assert result.is_authentic is True
    assert isinstance(result.data, CRLVData)
    assert result.data.placa == "ABC1D23"
    assert result.data.placa_formatada == "ABC1D23"
    assert result.data.renavam == "11223344556"
    assert result.data.chassi == "9BWZZZ377VT004251"
    assert result.data.cpf_cnpj_formatado == "123.456.789-09"
    assert result.data.ano_fabricacao_modelo == "2023/2024"
    assert result.data.proprietario == "JOAO DA SILVA SAO PAULO"
    assert result.is_valid is True


def test_crlv_tampering_detection(rsa_material, cert_store, crlv_template_store):
    qr = build_multiblock_qr(
        CRLV_FIELDS,
        version=4,
        template_id=70,
        timestamp=TIMESTAMP,
        sign=rsa_material["sign"],
    )

    # Adultera um byte no meio do payload
    tampered = bytearray(qr)
    tampered[45] ^= 0xFF

    checker = DigitalDocumentChecker(certificates=cert_store, templates=crlv_template_store)
    result = checker.parse_bytes(bytes(tampered), now=datetime(2026, 2, 1, tzinfo=timezone.utc))

    # A assinatura DEVE falhar (não autêntico)
    assert result.is_authentic is False
    assert result.is_valid is False
    assert "assinatura não confere" in " ".join(result.errors).lower()


def test_crlv_multiblock_v6_base91(rsa_material, cert_store, crlv_template_store):
    qr = build_multiblock_qr(
        CRLV_FIELDS,
        version=6,
        template_id=62,
        timestamp=TIMESTAMP,
        sign=rsa_material["sign"],
    )

    checker = DigitalDocumentChecker(certificates=cert_store, templates=crlv_template_store)
    result = checker.parse_bytes(qr, now=datetime(2026, 2, 1, tzinfo=timezone.utc))

    assert result.is_parsed
    assert result.document_type == "crlv"
    assert result.template_id == 62
    assert result.is_authentic is True
    assert result.data.marca_modelo == "VW/GOL 1.0"

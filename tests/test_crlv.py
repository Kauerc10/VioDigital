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


def test_crlv_template_24_renave_alias_normalization(rsa_material, cert_store):
    """Garante que o Template 24 (CRVe RENAVE) e os aliases do Template 12 sejam normalizados."""
    handler = CRLVHandler()
    assert handler.matches(24, None)

    renave_fields = "^".join(
        [
            "1234567890",            # numero_crv
            "99887766554",           # codigo_seguranca
            "11223344556",           # renavam
            "QWE9A87",               # placa
            "PASSAGEIRO",            # especie
            "AUTOMOVEL",             # tipo_veiculo
            "PRATA",                 # cor
            "FLEX",                  # combustivel
            "SC",                    # placa_anterior_uf
            "9BWZZZ377VT004251",     # chassi
            "TOYOTA/COROLLA XEI",    # marca_modelo
            "2023",                  # ano_fabricacao
            "2024",                  # ano_modelo
            "PARTICULAR",            # categoria
            "0.40",                  # capacidade_carga
            "177",                   # potencia
            "1987",                  # cilindrada
            "1.80",                  # peso_bruto_total
            "M20A123456",            # motor
            "1.80",                  # cmt
            "2",                     # eixos
            "5",                     # lotacao
            "SEDAN",                 # carroceria
            "EMPRESA VEICULOS LTDA", # nome_proprietario
            "12345678000195",        # documento_proprietario
            "FLORIANOPOLIS",         # municipio_jurisdicao_veiculo
            "SC",                    # uf_jurisdicao_veiculo
            "10/01/2026",            # data_emissao_crv
        ]
    )

    qr = build_multiblock_qr(
        renave_fields,
        version=4,
        template_id=24,
        timestamp=TIMESTAMP,
        sign=rsa_material["sign"],
    )

    checker = DigitalDocumentChecker(certificates=cert_store)
    result = checker.parse_bytes(qr, now=datetime(2026, 2, 1, tzinfo=timezone.utc))

    assert result.is_parsed
    assert result.document_type == "crlv"
    assert isinstance(result.data, CRLVData)
    assert result.data.placa_formatada == "QWE9A87"
    assert result.data.proprietario == "EMPRESA VEICULOS LTDA"
    assert result.data.cpf_cnpj_formatado == "12.345.678/0001-95"
    assert result.data.codigo_seguranca_cla == "99887766554"
    assert result.data.numero_crv == "1234567890"
    assert result.data.cilindradas == "1987"
    assert result.data.pbt == "1.80"
    assert result.data.local == "FLORIANOPOLIS"
    assert result.data.data == "10/01/2026"


def test_atpv_template_43_parse_and_authenticate(rsa_material, cert_store):
    """Garante que o Template 43 (ATPVe) é interpretado pelo ATPVHandler com todos os 26 campos."""
    from vioweb.core.documents.atpv import ATPVData, ATPVHandler
    from vioweb.core.registry import default_templates

    handler = ATPVHandler()
    assert handler.matches(43, None)

    atpv_fields = "^".join(
        [
            "00012345678",            # numero_atpv
            "ABC1D23",                # placa
            "11223344556",            # renavam
            "9BWZZZ377VT004251",      # chassi
            "R$ 85.000,00",           # valor_venda
            "FLORIANOPOLIS",          # local_venda
            "10/11/2026",             # data_venda
            "9876543210",             # numero_crv
            "12345678901",            # codigo_seguranca_crv
            "SC",                     # uf_emissao_crv
            "05/01/2024",             # data_emissao_crv
            "VW/T-CROSS HIGHLINE",    # marca_modelo
            "CINZA",                  # cor
            "2023",                   # ano_fabricacao
            "2024",                   # ano_modelo
            "32500",                  # kilometragem_hodometro
            "CARLOS VENDEDOR SILVA",  # nome_vendedor
            "09854034976",            # documento_vendedor
            "carlos@email.com",       # email_vendedor
            "FLORIANOPOLIS",          # municipio_vendedor
            "SC",                     # uf_vendedor
            "MARCOS COMPRADOR SOUZA", # nome_comprador
            "12345678909",            # documento_comprador
            "marcos@email.com",       # email_comprador
            "SAO JOSE",               # municipio_comprador
            "SC",                     # uf_comprador
        ]
    )

    qr = build_multiblock_qr(
        atpv_fields,
        version=4,
        template_id=43,
        timestamp=TIMESTAMP,
        sign=rsa_material["sign"],
    )

    checker = DigitalDocumentChecker(certificates=cert_store, templates=default_templates())
    result = checker.parse_bytes(qr, now=datetime(2026, 11, 10, tzinfo=timezone.utc))

    assert result.is_parsed
    assert result.document_type == "atpv"
    assert isinstance(result.data, ATPVData)
    assert result.data.numero_atpv == "00012345678"
    assert result.data.placa_formatada == "ABC1D23"
    assert result.data.renavam_formatado == "11223344556"
    assert result.data.valor_venda == "R$ 85.000,00"
    assert result.data.nome_vendedor == "CARLOS VENDEDOR SILVA"
    assert result.data.documento_vendedor_formatado == "098.540.349-76"
    assert result.data.nome_comprador == "MARCOS COMPRADOR SOUZA"
    assert result.data.documento_comprador_formatado == "123.456.789-09"
    assert result.data.municipio_comprador == "SAO JOSE"

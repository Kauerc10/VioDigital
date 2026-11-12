from datetime import datetime, timezone

from viodigital.core import DigitalDocumentChecker
from viodigital.core.documents.cnh import CNHData
from tests.conftest import build_v2_qr

CNH_FIELDS = "^".join(
    [
        "THAIS FREITAS DE CARVALHO",
        "435341700 SESP SP",
        "06771993922",
        "24/07/1987",
        "ELLIS EVANGELISTA LIMA",
        "DORALICE FREITAS LIMA",
        "",
        "",
        "B",
        "12993042523",
        "08/12/2031",
        "21/01/2020",
        "",
        "CURITIBA",
        "PR",
        "08/12/2021",
        "12993042523",
        "PR12993042523",
    ]
).upper()

TIMESTAMP = 0x60C38DB5


def test_cnh_parse_and_authenticate(rsa_material, cert_store):
    from viodigital.core.registry import TemplateStore

    cnh_template_store = TemplateStore.from_json(
        [
            {
                "id": 4,
                "name": "CNH",
                "owner": {"id": 1, "name": "SENATRAN"},
                "fields": [
                    {"name": n}
                    for n in [
                        "nome",
                        "identidade",
                        "cpf",
                        "data_nascimento",
                        "filiacao_pai",
                        "filiacao_mae",
                        "permissao",
                        "acc",
                        "categoria",
                        "numero_registro",
                        "data_validade",
                        "data_primeira_habilitacao",
                        "observacoes",
                        "local_emissao",
                        "uf_emissao",
                        "data_emissao",
                        "numero_validacao_cnh",
                        "numero_renach",
                    ]
                ],
                "certificate_group": {"id": "test-group"},
                "sandbox": False,
            }
        ]
    )

    qr = build_v2_qr(CNH_FIELDS, template_id=4, timestamp=TIMESTAMP, sign=rsa_material["sign"])
    checker = DigitalDocumentChecker(certificates=cert_store, templates=cnh_template_store)
    result = checker.parse_bytes(qr, now=datetime(2025, 1, 1, tzinfo=timezone.utc))

    assert result.is_parsed
    assert result.document_type == "cnh"
    assert result.template_id == 4
    assert result.is_authentic is True
    assert isinstance(result.data, CNHData)
    assert result.data.nome == "THAIS FREITAS DE CARVALHO"
    assert result.data.categoria == "B"
    assert result.data.cpf_formatado == "067.719.939-22"
    assert result.data.identidade == "435341700 SESP SP"
    assert result.data.data_nascimento == "24/07/1987"
    assert result.data.filiacao_pai == "ELLIS EVANGELISTA LIMA"
    assert result.data.filiacao_mae == "DORALICE FREITAS LIMA"
    assert result.data.data_primeira_habilitacao == "21/01/2020"
    assert result.data.data_validade == "08/12/2031"
    assert result.data.numero_renach == "PR12993042523"
    assert result.data.numero_validacao_cnh == "12993042523"
    assert result.data.local_emissao == "CURITIBA"
    assert result.data.uf_emissao == "PR"

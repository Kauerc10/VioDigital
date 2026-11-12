"""Submódulo da ATPV-e (Autorização para Transferência de Propriedade do Veículo Eletrônica).

Template ``43`` do emissor SENATRAN. Os campos são separados por ``^`` na
ordem declarada pelo template.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from ..models import RawPayload, Template
from ._helpers import map_fields
from .base import DocumentData, DocumentHandler

FIELD_ORDER_DEFAULT = [
    "numero_atpv",
    "placa",
    "renavam",
    "chassi",
    "valor_venda",
    "local_venda",
    "data_venda",
    "numero_crv",
    "codigo_seguranca_crv",
    "uf_emissao_crv",
    "data_emissao_crv",
    "marca_modelo",
    "cor",
    "ano_fabricacao",
    "ano_modelo",
    "kilometragem_hodometro",
    "nome_vendedor",
    "documento_vendedor",
    "email_vendedor",
    "municipio_vendedor",
    "uf_vendedor",
    "nome_comprador",
    "documento_comprador",
    "email_comprador",
    "municipio_comprador",
    "uf_comprador",
]


def _format_cpf_cnpj(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    digits = re.sub(r"\D", "", val)
    if len(digits) == 11:
        return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"
    if len(digits) == 14:
        return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"
    return val


@dataclass
class ATPVData(DocumentData):
    numero_atpv: Optional[str] = None
    placa: Optional[str] = None
    renavam: Optional[str] = None
    chassi: Optional[str] = None
    valor_venda: Optional[str] = None
    local_venda: Optional[str] = None
    data_venda: Optional[str] = None
    numero_crv: Optional[str] = None
    codigo_seguranca_crv: Optional[str] = None
    uf_emissao_crv: Optional[str] = None
    data_emissao_crv: Optional[str] = None
    marca_modelo: Optional[str] = None
    cor: Optional[str] = None
    ano_fabricacao: Optional[str] = None
    ano_modelo: Optional[str] = None
    kilometragem_hodometro: Optional[str] = None
    nome_vendedor: Optional[str] = None
    documento_vendedor: Optional[str] = None
    email_vendedor: Optional[str] = None
    municipio_vendedor: Optional[str] = None
    uf_vendedor: Optional[str] = None
    nome_comprador: Optional[str] = None
    documento_comprador: Optional[str] = None
    email_comprador: Optional[str] = None
    municipio_comprador: Optional[str] = None
    uf_comprador: Optional[str] = None

    @property
    def placa_formatada(self) -> Optional[str]:
        if not self.placa:
            return None
        clean = re.sub(r"[^A-Za-z0-9]", "", self.placa).upper()
        if len(clean) == 7:
            if clean[3].isdigit() and clean[4].isdigit():
                return f"{clean[0:3]}-{clean[3:7]}"
            return clean
        return self.placa.strip().upper()

    @property
    def renavam_formatado(self) -> Optional[str]:
        if not self.renavam:
            return None
        digits = re.sub(r"\D", "", self.renavam)
        if len(digits) == 9:
            return digits.zfill(11)
        return digits or self.renavam

    @property
    def ano_fabricacao_modelo(self) -> Optional[str]:
        fab = self.ano_fabricacao or ""
        mod = self.ano_modelo or ""
        if fab and mod:
            return f"{fab}/{mod}"
        return fab or mod or None

    @property
    def documento_vendedor_formatado(self) -> Optional[str]:
        return _format_cpf_cnpj(self.documento_vendedor)

    @property
    def documento_comprador_formatado(self) -> Optional[str]:
        return _format_cpf_cnpj(self.documento_comprador)


class ATPVHandler(DocumentHandler):
    type_name = "atpv"
    display_name = "ATPV-e (Autorização para Transferência de Propriedade de Veículo)"
    template_ids = (43,)

    def matches(self, template_id: int, template: Optional[Template]) -> bool:
        if template_id in self.template_ids:
            return True
        if template and template.name:
            norm = template.name.strip().upper()
            return norm in ("ATPVE", "ATPV-E", "ATPV")
        return False

    def build(self, payload: RawPayload, template: Optional[Template]) -> ATPVData:
        return map_fields(ATPVData(), payload, template, FIELD_ORDER_DEFAULT)

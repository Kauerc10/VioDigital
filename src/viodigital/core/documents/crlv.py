"""Submódulo do CRLV (Certificado de Registro e Licenciamento de Veículo) digital.

Templates ``10``, ``12``, ``62`` e ``70`` do emissor SENATRAN.
Os campos são separados por ``^`` na ordem declarada pelo template.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from ..models import RawPayload, Template
from ._helpers import map_fields
from .base import DocumentData, DocumentHandler

FIELD_ORDER_DEFAULT = [
    "codigo_seguranca_cla",
    "numero_crv",
    "uf",
    "renavam",
    "rntrc",
    "exercicio",
    "nome",
    "cpf_cnpj",
    "placa",
    "chassi",
    "especie",
    "tipo",
    "carroceria",
    "combustivel",
    "ano_fabricacao",
    "ano_modelo",
    "marca_modelo",
    "lotacao",
    "potencia",
    "cilindradas",
    "categoria",
    "cor",
    "motor",
    "capacidade_maxima_carga",
    "pbt",
    "cmt",
    "eixos",
    "local",
    "data",
    "observacoes",
]


@dataclass
class CRLVData(DocumentData):
    codigo_seguranca_cla: Optional[str] = None
    numero_crv: Optional[str] = None
    uf: Optional[str] = None
    renavam: Optional[str] = None
    rntrc: Optional[str] = None
    exercicio: Optional[str] = None
    nome: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    placa: Optional[str] = None
    chassi: Optional[str] = None
    especie: Optional[str] = None
    tipo: Optional[str] = None
    carroceria: Optional[str] = None
    combustivel: Optional[str] = None
    ano_fabricacao: Optional[str] = None
    ano_modelo: Optional[str] = None
    marca_modelo: Optional[str] = None
    lotacao: Optional[str] = None
    potencia: Optional[str] = None
    cilindradas: Optional[str] = None
    categoria: Optional[str] = None
    cor: Optional[str] = None
    motor: Optional[str] = None
    capacidade_maxima_carga: Optional[str] = None
    pbt: Optional[str] = None
    cmt: Optional[str] = None
    eixos: Optional[str] = None
    local: Optional[str] = None
    data: Optional[str] = None
    observacoes: Optional[str] = None
    # Aliases presentes nos templates 10, 12 e 24 (CRVe RENAVE)
    codigo_seguranca: Optional[str] = None
    numero_tipografico: Optional[str] = None
    numero: Optional[str] = None
    via: Optional[str] = None
    capacidade: Optional[str] = None
    capacidade_carga: Optional[str] = None
    validade: Optional[str] = None
    tipo_veiculo: Optional[str] = None
    placa_anterior_uf: Optional[str] = None
    cilindrada: Optional[str] = None
    peso_bruto_total: Optional[str] = None
    nome_proprietario: Optional[str] = None
    documento_proprietario: Optional[str] = None
    municipio_jurisdicao_veiculo: Optional[str] = None
    uf_jurisdicao_veiculo: Optional[str] = None
    data_emissao_crv: Optional[str] = None

    @property
    def proprietario(self) -> Optional[str]:
        """Alias conveniente para o nome do proprietário."""
        return self.nome or self.nome_proprietario

    @property
    def placa_formatada(self) -> Optional[str]:
        if not self.placa:
            return None
        clean = re.sub(r"[^A-Za-z0-9]", "", self.placa).upper()
        if len(clean) == 7:
            # Mercosul: 3 letras, 1 numero, 1 letra, 2 numeros (ex: ABC1D23)
            # Cinza antiga: 3 letras, 4 numeros (ex: ABC-1234)
            if clean[3].isdigit() and clean[4].isdigit():
                return f"{clean[0:3]}-{clean[3:7]}"
            return clean
        return self.placa.strip().upper()

    @property
    def cpf_cnpj_formatado(self) -> Optional[str]:
        raw_doc = self.cpf_cnpj or self.documento_proprietario
        if not raw_doc:
            return None
        digits = re.sub(r"\D", "", raw_doc)
        if len(digits) == 11:
            return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"
        elif len(digits) == 14:
            return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"
        return raw_doc

    @property
    def renavam_formatado(self) -> Optional[str]:
        if not self.renavam:
            return None
        digits = re.sub(r"\D", "", self.renavam)
        # RENAVAM can be 9 or 11 digits
        if len(digits) == 9:
            return f"{digits.zfill(11)}"
        return digits or self.renavam

    @property
    def ano_fabricacao_modelo(self) -> Optional[str]:
        fab = self.ano_fabricacao or ""
        mod = self.ano_modelo or ""
        if fab and mod:
            return f"{fab}/{mod}"
        return fab or mod or None


class CRLVHandler(DocumentHandler):
    type_name = "crlv"
    display_name = "CRLV Digital"
    template_ids = (10, 12, 24, 62, 70)

    def matches(self, template_id: int, template: Optional[Template]) -> bool:
        if template_id in self.template_ids:
            return True
        if template and template.name:
            norm = template.name.strip().upper()
            return (
                norm in ("CRLV DIGITAL", "CRLV", "CERTIFICADO DE REGISTRO E LICENCIAMENTO DE VEÍCULO")
                or "CRLV" in norm
                or "CRVE" in norm
            )
        return False

    def build(self, payload: RawPayload, template: Optional[Template]) -> CRLVData:
        obj: CRLVData = map_fields(CRLVData(), payload, template, FIELD_ORDER_DEFAULT)  # type: ignore[assignment]
        # Normaliza aliases dos templates 10, 12 e 24 nos campos principais
        if not obj.nome and obj.nome_proprietario:
            obj.nome = obj.nome_proprietario
        if not obj.cpf_cnpj and obj.documento_proprietario:
            obj.cpf_cnpj = obj.documento_proprietario
        if not obj.codigo_seguranca_cla and obj.codigo_seguranca:
            obj.codigo_seguranca_cla = obj.codigo_seguranca
        if not obj.numero_crv and (obj.numero_tipografico or obj.numero):
            obj.numero_crv = obj.numero_tipografico or obj.numero
        if not obj.local and obj.municipio_jurisdicao_veiculo:
            obj.local = obj.municipio_jurisdicao_veiculo
        if not obj.uf and obj.uf_jurisdicao_veiculo:
            obj.uf = obj.uf_jurisdicao_veiculo
        if not obj.data and obj.data_emissao_crv:
            obj.data = obj.data_emissao_crv
        if not obj.tipo and obj.tipo_veiculo:
            obj.tipo = obj.tipo_veiculo
        if not obj.cilindradas and obj.cilindrada:
            obj.cilindradas = obj.cilindrada
        if not obj.pbt and obj.peso_bruto_total:
            obj.pbt = obj.peso_bruto_total
        if not obj.capacidade_maxima_carga and (obj.capacidade_carga or obj.capacidade):
            obj.capacidade_maxima_carga = obj.capacidade_carga or obj.capacidade
        return obj

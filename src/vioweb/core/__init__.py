"""VioWeb Core.

Biblioteca modular para parsing, verificação e validação de documentos
digitais oficiais brasileiros codificados em QRCode: o padrão SERPRO/VIO
(CRLV-e, CNH, ATPV-e, DNI, RG Digital e +160 templates) e a CIN — Carteira de
Identidade Nacional (token JWS assinado ES512).

Uso rápido::

    from vioweb.core import DigitalDocumentChecker

    checker = DigitalDocumentChecker()
    result = checker.parse_bytes(qr_bytes)
    print(result.document_type, result.is_authentic, result.is_valid)
    print(result.fields)
"""

from __future__ import annotations

from .checker import DigitalDocumentChecker
from .exceptions import (
    DecodeError,
    DigitalDocumentError,
    MissingDependencyError,
    ParseError,
    QRCodeNotFoundError,
    UnsupportedVersionError,
)
from .models import (
    Certificate,
    CINKey,
    DocumentResult,
    Envelope,
    Photo,
    SignatureInfo,
    Template,
)
from .presentation import present
from .registry import CertificateStore, CINKeyStore, TemplateStore
from .__meta__ import __version__

__all__ = [
    "DigitalDocumentChecker",
    "DocumentResult",
    "present",
    "SignatureInfo",
    "Photo",
    "Certificate",
    "CINKey",
    "Template",
    "Envelope",
    "CertificateStore",
    "CINKeyStore",
    "TemplateStore",
    "DigitalDocumentError",
    "ParseError",
    "DecodeError",
    "UnsupportedVersionError",
    "QRCodeNotFoundError",
    "MissingDependencyError",
    "__version__",
]

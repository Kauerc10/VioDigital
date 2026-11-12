from __future__ import annotations

import sys
import pytest

from viodigital.core import DigitalDocumentChecker
from viodigital.core.exceptions import MissingDependencyError
from tests.conftest import build_multiblock_qr
from tests.test_crlv import CRLV_FIELDS, TIMESTAMP


def test_core_parse_bytes_minimal_dependencies(rsa_material, cert_store, crlv_template_store):
    """Verifica que o core processa e autentica bytes sem depender de módulos de visão ou servidor."""
    qr_bytes = build_multiblock_qr(
        CRLV_FIELDS,
        version=4,
        template_id=70,
        timestamp=TIMESTAMP,
        sign=rsa_material["sign"],
    )

    checker = DigitalDocumentChecker(certificates=cert_store, templates=crlv_template_store)
    result = checker.parse_bytes(qr_bytes)

    assert result.is_parsed
    assert result.is_authentic
    assert result.document_type == "crlv"
    assert result.fields.get("placa") == "ABC1D23"


def test_parse_image_raises_missing_dependency_when_pillow_missing(monkeypatch):
    """Verifica que parse_image levanta MissingDependencyError quando Pillow está ausente."""
    monkeypatch.setitem(sys.modules, "PIL", None)
    monkeypatch.setitem(sys.modules, "PIL.Image", None)

    checker = DigitalDocumentChecker()
    with pytest.raises(MissingDependencyError) as exc_info:
        checker.parse_image(b"fake_image_bytes")

    assert "viodigital[vision]" in str(exc_info.value)


def test_read_qr_from_image_raises_missing_dependency_when_decoders_missing(monkeypatch):
    """Verifica que read_qr_from_image levanta MissingDependencyError quando nenhum leitor de QR está instalado."""
    from viodigital.core import qr

    monkeypatch.setitem(sys.modules, "zxingcpp", None)
    monkeypatch.setitem(sys.modules, "pyzbar", None)
    monkeypatch.setitem(sys.modules, "cv2", None)

    with pytest.raises(MissingDependencyError) as exc_info:
        qr.read_qr_from_image(b"fake_image_bytes")

    assert "viodigital[vision]" in str(exc_info.value)


def test_parse_pdf_raises_missing_dependency_when_pymupdf_missing(monkeypatch):
    """Verifica que parse_pdf levanta MissingDependencyError quando pymupdf está ausente."""
    monkeypatch.setitem(sys.modules, "pymupdf", None)

    checker = DigitalDocumentChecker()
    with pytest.raises(MissingDependencyError) as exc_info:
        checker.parse_pdf(b"%PDF-fake")

    assert "viodigital[vision]" in str(exc_info.value)

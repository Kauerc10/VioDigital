from __future__ import annotations

import base64
import pytest

from viodigital.core.codecs import base91
from viodigital.core.codecs.text import encode_6bit, encode_7bit
from viodigital.core.models import Certificate
from viodigital.core.registry import CertificateStore, TemplateStore


def build_v2_qr(fields_text: str, *, template_id: int, timestamp: int, sign) -> bytes:
    """Monta um QRCode v2 (CNH) e assina o dado reconstruído."""
    header = f"{timestamp:08x}{2:02x}".encode("latin-1")  # versão 2
    encoded_fields = encode_6bit(fields_text)
    prefix = template_id.to_bytes(2, "big") + len(encoded_fields).to_bytes(2, "big")
    signed_prefix = header + prefix + encoded_fields  # header + payload[0:i9]
    signature = sign(signed_prefix)  # 256 bytes (RSA)
    payload = prefix + encoded_fields + signature
    return header + payload


def encode_multiblock_fields(fields_text: str, version: int) -> bytes:
    """Codifica o bloco de campos no alfabeto usado por cada versão multibloco."""
    if version == 4:
        return encode_7bit(fields_text)
    if version == 5:
        return encode_6bit(fields_text)
    if version == 6:
        return base91.encode(fields_text.encode("latin-1")).encode("latin-1")
    raise ValueError(f"versão multibloco inesperada: {version}")


def build_multiblock_qr(
    fields_text: str,
    *,
    version: int,
    template_id: int,
    timestamp: int,
    sign,
    photo: bytes = b"",
    extra: bytes = b"",
) -> bytes:
    """Monta um QRCode multibloco (v4/v5/v6) e assina o dado reconstruído."""
    header = f"{timestamp:08x}{version:02x}".encode("latin-1")
    fields_block = encode_multiblock_fields(fields_text, version)

    b0 = template_id.to_bytes(2, "big")
    len2 = len(photo).to_bytes(2, "big")
    len3 = len(fields_block).to_bytes(2, "big")

    # signed = ts[4:8] + versao + b0 + len2 + foto + len3 + campos
    signed = (
        timestamp.to_bytes(8, "big")[4:8]
        + bytes([version])
        + b0
        + len2
        + photo
        + len3
        + fields_block
    )
    signature = sign(signed)
    len1 = len(signature).to_bytes(2, "big")

    payload = b0 + len1 + signature + len2 + photo + len3 + fields_block + extra
    return header + payload


@pytest.fixture
def rsa_material():
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub_der = key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    pub_b64 = base64.b64encode(pub_der).decode()

    def sign(data: bytes) -> bytes:
        return key.sign(data, padding.PKCS1v15(), hashes.SHA256())

    return {"sign": sign, "public_key_b64": pub_b64}


@pytest.fixture
def cert_store(rsa_material):
    from datetime import datetime, timezone

    cert = Certificate(
        id="test-cert",
        group_id="test-group",
        public_key_b64=rsa_material["public_key_b64"],
        valid_from=datetime(2000, 1, 1, tzinfo=timezone.utc),
        valid_until=datetime(2100, 1, 1, tzinfo=timezone.utc),
    )
    return CertificateStore([cert])


@pytest.fixture
def crlv_template_store():
    from viodigital.core.documents.crlv import FIELD_ORDER_DEFAULT

    payload = [
        {
            "id": 70,
            "name": "CRLV Digital",
            "owner": {"id": 1, "name": "SENATRAN"},
            "fields": [{"name": n} for n in FIELD_ORDER_DEFAULT],
            "certificate_group": {"id": "test-group"},
            "sandbox": False,
        },
        {
            "id": 62,
            "name": "CRLV Digital",
            "owner": {"id": 1, "name": "SENATRAN"},
            "fields": [{"name": n} for n in FIELD_ORDER_DEFAULT],
            "certificate_group": {"id": "test-group"},
            "sandbox": False,
        },
    ]
    return TemplateStore.from_json(payload)

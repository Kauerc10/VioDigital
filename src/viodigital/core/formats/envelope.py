"""Parsing do envelope externo do QRCode.

Reproduz ``com.google.android.gms.internal.measurement.D1.a([B)``:

* Se os 10 primeiros bytes forem ASCII hexadecimal (8 dígitos de timestamp +
  2 dígitos de versão), o cabeçalho é *hexadecimal* (10 bytes).
* Caso a decodificação hexadecimal falhe, o cabeçalho é *binário* (5 bytes):
  4 bytes big-endian de timestamp (segundos) + 1 byte de versão.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..exceptions import ParseError
from ..models import Envelope


def looks_like_external_qr(data: bytes) -> bool:
    """Identifica se os bytes do QRCode representam uma URL web ou código PIX/EMV."""
    if not data:
        return False
    stripped = data.lstrip()
    if stripped.startswith((b"http://", b"https://", b"HTTP://", b"HTTPS://", b"www.", b"WWW.")):
        return True
    if stripped.startswith(b"000201") and b"br.gov.bcb.pix" in stripped.lower():
        return True
    return False


def _try_hex_header(data: bytes) -> tuple[int, int] | None:
    if len(data) < 10:
        return None
    try:
        head = data[:10].decode("latin-1")
        if head.startswith("000201"):
            return None
        timestamp = int(head[:8], 16)
        version = int(head[8:10], 16)
    except (ValueError, UnicodeDecodeError):
        return None
    return timestamp, version


def is_vio_or_cin_qr(data: bytes) -> bool:
    """Retorna True se o payload decodifica como um envelope VIO suportado ou JWS da CIN."""
    if not data or len(data) < 10 or looks_like_external_qr(data):
        return False
    from .base import get_format
    from .jws import looks_like_compact_jws

    if looks_like_compact_jws(data):
        return True
    try:
        env = parse_envelope(data)
        fmt = get_format(env.version)
        if fmt is None:
            return False
        payload = fmt.parse(env)
        return bool(payload and payload.template_id >= 0 and (payload.field_values or payload.signature))
    except Exception:
        return False


def parse_envelope(data: bytes) -> Envelope:
    """Extrai timestamp, versão e payload de um QRCode."""
    if data is None or len(data) < 10:
        raise ParseError("dados insuficientes para um envelope válido")

    hex_header = _try_hex_header(data)
    if hex_header is not None:
        timestamp, version = hex_header
        header_format = "hex"
        payload = data[10:]
        raw_header = data[:10]
    else:
        if len(data) < 5:
            raise ParseError("cabeçalho binário incompleto")
        timestamp = int.from_bytes(data[0:4], "big") & 0xFFFFFFFF
        version = data[4] & 0xFFFFFF
        header_format = "binary"
        payload = data[5:]
        raw_header = data[:5]

    issued_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)

    return Envelope(
        raw=bytes(raw_header),
        header_format=header_format,
        version=version,
        issued_at=issued_at,
        issued_timestamp=timestamp,
        payload=bytes(payload),
    )

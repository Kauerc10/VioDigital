"""Módulo de compatibilidade e transição de VioWeb para VioDigital."""
from __future__ import annotations

import viodigital as viodigital
from viodigital import *  # noqa: F401, F403
from viodigital.core.__meta__ import __version__ as __version__

__all__ = ["viodigital", "__version__"]

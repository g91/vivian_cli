"""User-Agent string helpers — mirrors src/utils/userAgent.ts"""
from __future__ import annotations

try:
    from ..constants import PRODUCT_VERSION
except ImportError:
    PRODUCT_VERSION = "0.0.0"


def get_vivian_code_user_agent() -> str:
    """Return the Vivian CLI user-agent string."""
    return f"vivian-cli/{PRODUCT_VERSION}"

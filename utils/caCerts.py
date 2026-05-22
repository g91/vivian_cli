"""CA certificate loading — mirrors src/utils/caCerts.ts"""
from __future__ import annotations
import os
from functools import lru_cache
from typing import Optional

@lru_cache(maxsize=1)
def get_ca_certificates() -> Optional[str]:
    """Return custom CA certificate content if configured."""
    path = os.environ.get("vivian_CODE_CA_BUNDLE") or os.environ.get("NODE_EXTRA_CA_CERTS")
    if path and os.path.exists(path):
        with open(path, "r") as f:
            return f.read()
    return None

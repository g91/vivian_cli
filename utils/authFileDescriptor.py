"""Auth file descriptor — mirrors src/utils/authFileDescriptor.ts"""
from __future__ import annotations
from typing import Optional

def read_auth_from_fd(fd: int) -> Optional[str]:
    try:
        import os
        with os.fdopen(fd, "r") as f:
            return f.read().strip()
    except Exception:
        return None

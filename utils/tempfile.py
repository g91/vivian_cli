"""Temporary file utilities — mirrors src/utils/tempfile.ts"""
from __future__ import annotations

import hashlib
import os
import tempfile
import uuid


def generate_temp_file_path(
    prefix: str = "vivian-prompt",
    extension: str = ".md",
    *,
    content_hash: str | None = None,
) -> str:
    """Generate a temporary file path.

    If ``content_hash`` is provided, the identifier is derived from a
    SHA-256 hash of that string (first 16 hex chars), producing a stable
    path across process boundaries. Otherwise a random UUID is used.
    """
    if content_hash is not None:
        ident = hashlib.sha256(content_hash.encode()).hexdigest()[:16]
    else:
        ident = str(uuid.uuid4())
    return os.path.join(tempfile.gettempdir(), f"{prefix}-{ident}{extension}")

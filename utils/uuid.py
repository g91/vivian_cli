"""UUID utilities — mirrors src/utils/uuid.ts"""
from __future__ import annotations

import re
import uuid as _uuid
from typing import Optional

_UUID_REGEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def validate_uuid(maybe_uuid: object) -> Optional[str]:
    """Validate a UUID string. Returns the UUID string if valid, else None."""
    if not isinstance(maybe_uuid, str):
        return None
    return maybe_uuid if _UUID_REGEX.match(maybe_uuid) else None


def create_agent_id(label: Optional[str] = None) -> str:
    """Generate a new agent ID with optional label prefix.
    Format: a{label-}{16 hex chars}
    Example: 'aa3f2c1b4d5e6f7a8' or 'acompact-a3f2c1b4d5e6f7a8'
    """
    import secrets
    suffix = secrets.token_hex(8)
    if label:
        return f"a{label}-{suffix}"
    return f"a{suffix}"


def generate_uuid() -> str:
    """Generate a new UUID v4 string."""
    return str(_uuid.uuid4())

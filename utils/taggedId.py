"""Tagged ID encoding — mirrors src/utils/taggedId.ts"""
from __future__ import annotations

_BASE58_CHARS = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_VERSION = "01"
_ENCODED_LENGTH = 22  # ceil(128 / log2(58)) = 22


def _base58_encode(n: int) -> str:
    """Encode a 128-bit unsigned integer as a fixed-length base58 string."""
    base = len(_BASE58_CHARS)
    result = [_BASE58_CHARS[0]] * _ENCODED_LENGTH
    i = _ENCODED_LENGTH - 1
    value = n
    while value > 0:
        rem = value % base
        result[i] = _BASE58_CHARS[rem]
        value //= base
        i -= 1
    return "".join(result)


def _uuid_to_int(uuid: str) -> int:
    """Parse a UUID string (with or without hyphens) into a 128-bit int."""
    hex_str = uuid.replace("-", "")
    if len(hex_str) != 32:
        raise ValueError(f"Invalid UUID hex length: {len(hex_str)}")
    return int(hex_str, 16)


def to_tagged_id(tag: str, uuid: str) -> str:
    """Convert a UUID to a tagged ID in the API's format.

    Example: ``to_tagged_id("user", "...uuid...")`` → ``"user_01PaGUP2..."``

    Must stay in sync with api/api/common/utils/tagged_id.py.
    """
    n = _uuid_to_int(uuid)
    return f"{tag}_{_VERSION}{_base58_encode(n)}"

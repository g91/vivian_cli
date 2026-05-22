"""JSON utilities — mirrors src/utils/json.ts"""
from __future__ import annotations

import json as _json
from typing import Any


def parse_json(text: str, default: Any = None) -> Any:
    """Parse JSON string, returning `default` on failure."""
    try:
        return _json.loads(text)
    except (_json.JSONDecodeError, ValueError):
        return default


def stringify_json(value: Any, *, indent: int | None = None, sort_keys: bool = False) -> str:
    """Serialize value to JSON string."""
    return _json.dumps(value, indent=indent, sort_keys=sort_keys, ensure_ascii=False)


def safe_parse(text: str) -> tuple[Any, Exception | None]:
    """Parse JSON returning (value, None) on success or (None, error) on failure."""
    try:
        return _json.loads(text), None
    except Exception as e:
        return None, e

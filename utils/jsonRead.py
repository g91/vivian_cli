"""JSON file reading utilities — mirrors src/utils/jsonRead.ts"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


def strip_bom(content: str) -> str:
    """Strip UTF-8 BOM (\\ufeff) from the start of a string."""
    return content.lstrip("\ufeff")


def read_json_file(path: str | Path) -> Any:
    """Read and parse a JSON file, stripping BOM if present."""
    text = Path(path).read_text(encoding="utf-8")
    return json.loads(strip_bom(text))


def try_read_json_file(path: str | Path, default: Any = None) -> Any:
    """Read and parse a JSON file, returning `default` if the file doesn't exist
    or parsing fails.
    """
    try:
        return read_json_file(path)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default

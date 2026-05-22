"""Vim motion helpers — mirrors src/vim/motions.ts."""
from __future__ import annotations

from typing import Any


def _call(cursor: Any, name: str) -> Any:
    method = getattr(cursor, name)
    return method()


def resolveMotion(key: str, cursor: Any, count: int) -> Any:
    result = cursor
    for _ in range(count):
        next_cursor = applySingleMotion(key, result)
        if hasattr(next_cursor, "equals") and next_cursor.equals(result):
            break
        if next_cursor == result:
            break
        result = next_cursor
    return result


def applySingleMotion(key: str, cursor: Any) -> Any:
    mapping = {
        "h": "left",
        "l": "right",
        "j": "downLogicalLine",
        "k": "upLogicalLine",
        "gj": "down",
        "gk": "up",
        "w": "nextVimWord",
        "b": "prevVimWord",
        "e": "endOfVimWord",
        "W": "nextWORD",
        "B": "prevWORD",
        "E": "endOfWORD",
        "0": "startOfLogicalLine",
        "^": "firstNonBlankInLogicalLine",
        "$": "endOfLogicalLine",
        "G": "startOfLastLine",
    }
    method_name = mapping.get(key)
    if method_name is None or not hasattr(cursor, method_name):
        return cursor
    return _call(cursor, method_name)


def isInclusiveMotion(key: str) -> bool:
    return key in {"e", "E", "$"}


def isLinewiseMotion(key: str) -> bool:
    return key in {"j", "k", "G", "gg"}


resolve_motion = resolveMotion
apply_single_motion = applySingleMotion
is_inclusive_motion = isInclusiveMotion
is_linewise_motion = isLinewiseMotion
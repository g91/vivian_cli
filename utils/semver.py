"""Semver comparison utilities — mirrors src/utils/semver.ts"""
from __future__ import annotations

import re
from typing import Literal


def _parse(v: str) -> tuple[int, int, int]:
    """Parse a semver string into a (major, minor, patch) tuple, lenient."""
    v = v.lstrip("v").strip()
    parts = re.split(r"[-+]", v)[0].split(".")
    try:
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, patch)
    except (ValueError, IndexError):
        return (0, 0, 0)


def order(a: str, b: str) -> Literal[-1, 0, 1]:
    """Compare two semver strings. Returns -1, 0, or 1."""
    pa, pb = _parse(a), _parse(b)
    if pa < pb:
        return -1
    if pa > pb:
        return 1
    return 0


def gt(a: str, b: str) -> bool:
    return order(a, b) == 1


def gte(a: str, b: str) -> bool:
    return order(a, b) >= 0


def lt(a: str, b: str) -> bool:
    return order(a, b) == -1


def lte(a: str, b: str) -> bool:
    return order(a, b) <= 0


def satisfies(version: str, range_str: str) -> bool:
    """Simple semver range check. Supports ^, ~, >=, <=, >, <, = prefixes."""
    range_str = range_str.strip()
    if range_str.startswith("^"):
        req = _parse(range_str[1:])
        ver = _parse(version)
        if req[0] == 0:
            if req[1] == 0:
                return ver == req
            return ver[0] == req[0] and ver[1] == req[1] and ver >= req
        return ver[0] == req[0] and ver >= req
    if range_str.startswith("~"):
        req = _parse(range_str[1:])
        ver = _parse(version)
        return ver[0] == req[0] and ver[1] == req[1] and ver >= req
    if range_str.startswith(">="):
        return gte(version, range_str[2:])
    if range_str.startswith("<="):
        return lte(version, range_str[2:])
    if range_str.startswith(">"):
        return gt(version, range_str[1:])
    if range_str.startswith("<"):
        return lt(version, range_str[1:])
    # Exact match or = prefix
    return order(version, range_str.lstrip("=")) == 0

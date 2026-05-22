"""Set utilities — mirrors src/utils/set.ts"""
from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def difference(a: set, b: set) -> set:
    """Return elements in a that are not in b."""
    return a - b


def intersects(a: set, b: set) -> bool:
    """Return True if a and b share at least one element."""
    if not a or not b:
        return False
    return not a.isdisjoint(b)


def every(a: set, b: set) -> bool:
    """Return True if every element of a is in b."""
    return a.issubset(b)


def union(a: set, b: set) -> set:
    """Return a new set containing all elements from a and b."""
    return a | b

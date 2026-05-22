"""Array utilities — mirrors src/utils/array.ts"""
from __future__ import annotations

from typing import Callable, Iterable, TypeVar

T = TypeVar("T")
A = TypeVar("A")


def intersperse(items: list[A], separator: Callable[[int], A]) -> list[A]:
    """Insert separator(i) between every two elements of items."""
    result: list[A] = []
    for i, item in enumerate(items):
        if i:
            result.append(separator(i))
        result.append(item)
    return result


def count(arr: Iterable[T], pred: Callable[[T], object]) -> int:
    """Count elements of arr for which pred is truthy."""
    return sum(1 for x in arr if pred(x))


def uniq(xs: Iterable[T]) -> list[T]:
    """Return unique elements of xs preserving order."""
    return list(dict.fromkeys(xs))

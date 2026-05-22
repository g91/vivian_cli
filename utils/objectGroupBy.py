"""Object groupBy — mirrors src/utils/objectGroupBy.ts"""
from __future__ import annotations

from collections import defaultdict
from typing import Callable, Dict, Iterable, List, TypeVar

T = TypeVar("T")
K = TypeVar("K")


def object_group_by(
    items: Iterable[T],
    key_selector: Callable[[T, int], K],
) -> Dict[K, List[T]]:
    """Group items by a key derived from each item and its index.

    Mirrors Object.groupBy() / objectGroupBy() from objectGroupBy.ts.
    """
    result: dict = {}
    for index, item in enumerate(items):
        key = key_selector(item, index)
        if key not in result:
            result[key] = []
        result[key].append(item)
    return result


objectGroupBy = object_group_by

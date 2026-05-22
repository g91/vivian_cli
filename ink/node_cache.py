"""Port of src/ink/node-cache.ts."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .dom import DOMElement

CachedLayout = dict[str, int]

_node_cache: dict[int, CachedLayout] = {}
_pending_clears: dict[int, list[dict[str, int]]] = {}
_absolute_node_removed = False


def getNodeCache() -> dict[int, CachedLayout]:
    return _node_cache


def getCachedLayout(node: DOMElement) -> CachedLayout | None:
    return _node_cache.get(id(node))


def setCachedLayout(node: DOMElement, layout: CachedLayout) -> None:
    _node_cache[id(node)] = layout


def deleteCachedLayout(node: DOMElement) -> None:
    _node_cache.pop(id(node), None)


def addPendingClear(parent: DOMElement, rect: dict[str, int], isAbsolute: bool) -> None:
    global _absolute_node_removed
    pid = id(parent)
    if pid in _pending_clears:
        _pending_clears[pid].append(rect)
    else:
        _pending_clears[pid] = [rect]
    if isAbsolute:
        _absolute_node_removed = True


def getPendingClears(parent: DOMElement) -> list[dict[str, int]]:
    return _pending_clears.pop(id(parent), [])


def consumeAbsoluteRemovedFlag() -> bool:
    global _absolute_node_removed
    had = _absolute_node_removed
    _absolute_node_removed = False
    return had


node_cache = _node_cache
pending_clears = _pending_clears
get_node_cache = getNodeCache
get_cached_layout = getCachedLayout
set_cached_layout = setCachedLayout
delete_cached_layout = deleteCachedLayout
add_pending_clear = addPendingClear
get_pending_clears = getPendingClears
consume_absolute_removed_flag = consumeAbsoluteRemovedFlag

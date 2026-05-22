"""Byline component — mirrors src/components/design-system/Byline.tsx."""

from __future__ import annotations

from typing import Any


def Byline(children: list[Any] | tuple[Any, ...]) -> str | None:
    valid_children = [str(child) for child in children if child not in (None, False, "")]
    if not valid_children:
        return None
    return " · ".join(valid_children)


__all__ = ["Byline"]
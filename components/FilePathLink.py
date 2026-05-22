"""FilePathLink component — mirrors src/components/FilePathLink.tsx."""

from __future__ import annotations

from pathlib import Path

from ..ink.termio.osc import link


def FilePathLink(filePath: str, children: str | None = None) -> str:
    uri = Path(filePath).resolve().as_uri()
    text = children or filePath
    return f"{link(uri)}{text}{link('')}"


__all__ = ["FilePathLink"]
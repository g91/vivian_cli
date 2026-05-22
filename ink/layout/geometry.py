"""Port of src/ink/layout/geometry.ts."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Point:
    x: int = 0
    y: int = 0


@dataclass
class Size:
    width: int = 0
    height: int = 0


@dataclass
class Rectangle:
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

"""vivian.md file utilities — mirrors src/utils/vivianmd.ts"""
from __future__ import annotations
import os
from typing import Optional

def find_vivian_md(directory: str) -> Optional[str]:
    """Find a vivian.md file in directory or parents."""
    path = os.path.abspath(directory)
    while True:
        candidate = os.path.join(path, "vivian.md")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent

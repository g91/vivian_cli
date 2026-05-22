"""Add dir validation — mirrors src/commands/add-dir/validation.ts."""
from __future__ import annotations
import os

def validateDirectory(path: str) -> bool:
    return os.path.isdir(path)

validate_directory = validateDirectory

"""FileEditTool types — mirrors src/tools/FileEditTool/types.ts"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class EditResult:
    """Result of an edit operation."""
    filePath: str
    success: bool
    message: str = ""
    diff: str = ""
    hasChanges: bool = False
    newContent: Optional[str] = None
    error: Optional[str] = None

@dataclass
class FileEditInput:
    """Input for the FileEdit tool."""
    file_path: str
    old_string: str
    new_string: str
    expected_hash: Optional[str] = None
    replace_all: bool = False

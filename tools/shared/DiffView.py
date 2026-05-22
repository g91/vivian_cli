"""Shared diff rendering — mirrors src/tools/shared/DiffView.tsx"""
from __future__ import annotations
import difflib
from typing import List, Optional


def renderUnifiedDiff(
    original: str,
    modified: str,
    filePath: str = "",
    contextLines: int = 3,
) -> str:
    """Render a unified diff between original and modified content."""
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)
    diff = list(difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{filePath}" if filePath else "original",
        tofile=f"b/{filePath}" if filePath else "modified",
        n=contextLines,
    ))
    return "".join(diff)


def renderInlineDiff(original: str, modified: str) -> str:
    """Render an inline diff showing word-level changes."""
    matcher = difflib.SequenceMatcher(None, original.split(), modified.split())
    parts: List[str] = []
    for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
        if opcode == "equal":
            parts.append(" ".join(original.split()[a0:a1]))
        elif opcode == "replace":
            parts.append(f"[-{' '.join(original.split()[a0:a1])}]")
            parts.append(f"[+{' '.join(modified.split()[b0:b1])}]")
        elif opcode == "delete":
            parts.append(f"[-{' '.join(original.split()[a0:a1])}]")
        elif opcode == "insert":
            parts.append(f"[+{' '.join(modified.split()[b0:b1])}]")
    return " ".join(parts)

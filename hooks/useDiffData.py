"""Diff data hook — mirrors src/hooks/useDiffData.ts."""
from __future__ import annotations
from typing import Any

def useDiffData(filePath: str | None = None) -> dict[str, Any]:
    """Retrieve and manage diff data for a file."""
    return {
        'filePath': filePath,
        'diff': None,
        'loading': False,
        'error': None,
    }

use_diff_data = useDiffData

"""Port of src/hooks/useTerminalSize.ts."""
from __future__ import annotations


def useTerminalSize(size_context):
    if not size_context:
        raise RuntimeError('useTerminalSize must be used within an Ink App component')
    return size_context

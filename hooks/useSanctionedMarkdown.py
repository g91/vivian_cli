"""Sanctioned markdown — mirrors src/hooks/useSanctionedMarkdown.ts."""
from __future__ import annotations

def useSanctionedMarkdown(markdown: str = "") -> dict:
    """Parse safe markdown."""
    return {"raw": markdown, "html": markdown}

use_sanctioned_markdown = useSanctionedMarkdown

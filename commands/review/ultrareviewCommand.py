"""ultrareviewCommand — mirrors src/commands/review/ultrareviewCommand.tsx.

Ultrareview: deep bug-finding review that runs remotely.
"""

from __future__ import annotations


async def ultrareview_command(prompt: str = "") -> str:
    """Launch an ultrareview session."""
    return f"Ultrareview: Deep analysis started. This may take 10-20 minutes."

"""UltrareviewOverageDialog — mirrors src/commands/review/UltrareviewOverageDialog.tsx.

Dialog shown when free ultrareviews are exhausted.
"""

from __future__ import annotations


def show_overage_dialog() -> str:
    """Show the overage dialog message."""
    return "You've used all your free ultrareviews this month. Upgrade to continue."

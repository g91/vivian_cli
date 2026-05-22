"""Port of src/utils/shell/resolveDefaultShell.ts."""
from __future__ import annotations

from ..settings.settings import getInitialSettings


def resolveDefaultShell() -> str:
    """Resolve the default shell for input-box `!` commands.

Resolution order (docs/design/ps-shell-selection.md §4.2):
settings.defaultShell → 'bash'

Platform default is 'bash' everywhere — we do NOT auto-flip Windows to
PowerShell (would break existing Windows users with bash hooks)."""
    settings = getInitialSettings() or {}
    return settings.get("defaultShell") or "bash"


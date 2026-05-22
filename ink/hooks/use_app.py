"""Port of src/ink/hooks/use-app.ts."""
from __future__ import annotations

from ..components.AppContext import AppContextProps, getAppContext


def useApp() -> AppContextProps:
    """Get the current Ink app context."""
    return getAppContext()


use_app = useApp

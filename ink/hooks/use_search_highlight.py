"""Port of src/ink/hooks/use-search-highlight.ts."""
from __future__ import annotations

from ..components.StdinContext import getStdinContext


def useSearchHighlight(query: str) -> None:
    """Apply search highlighting for the given query."""
    context = getStdinContext()
    app = context.app
    if app is not None and hasattr(app, "setSearchHighlight"):
        app.setSearchHighlight(query)


use_search_highlight = useSearchHighlight

"""XML utilities — mirrors src/utils/xml.ts"""
from __future__ import annotations

import html


def escape_xml(s: str) -> str:
    """Escape special XML characters in a string."""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def unescape_xml(s: str) -> str:
    """Unescape XML entities back to characters."""
    return html.unescape(s)

"""AddMarketplace — mirrors src/commands/plugin/AddMarketplace.tsx.

UI for adding a new plugin marketplace.
"""

from __future__ import annotations


def add_marketplace(url: str = "", name: str = "") -> dict:
    """Add a new plugin marketplace."""
    return {"url": url, "name": name or url, "enabled": True}

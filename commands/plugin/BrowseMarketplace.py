"""BrowseMarketplace — mirrors src/commands/plugin/BrowseMarketplace.tsx.

Browse available plugins in the marketplace.
"""

from __future__ import annotations


def browse_marketplace(query: str = "") -> list[dict]:
    """Browse the plugin marketplace."""
    return [{"name": "example-plugin", "description": "An example plugin", "version": "1.0.0"}]

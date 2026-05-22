"""DiscoverPlugins — mirrors src/commands/plugin/DiscoverPlugins.tsx.

Discover and recommend plugins based on project context.
"""

from __future__ import annotations


def discover_plugins(project_type: str = "") -> list[dict]:
    """Discover recommended plugins for a project type."""
    recommendations = {
        "python": [{"name": "pytest", "description": "Test runner integration"}],
        "node": [{"name": "eslint", "description": "Linting integration"}],
        "rust": [{"name": "cargo", "description": "Cargo build integration"}],
    }
    return recommendations.get(project_type.lower(), [])

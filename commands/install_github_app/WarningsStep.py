"""WarningsStep — mirrors src/commands/install-github-app/WarningsStep.tsx."""
from __future__ import annotations

from ...constants.github_app import GITHUB_ACTION_SETUP_DOCS_URL


def render_warnings_step(warnings: list[dict]) -> dict:
    return {
        "title": "Setup Warnings",
        "subtitle": "We found some potential issues, but you can continue anyway",
        "warnings": [
            {
                "title": warning.get("title"),
                "message": warning.get("message"),
                "instructions": warning.get("instructions", []),
            }
            for warning in warnings
        ],
        "continue_prompt": "Press Enter to continue anyway, or Ctrl+C to exit and fix issues",
        "docs_url": GITHUB_ACTION_SETUP_DOCS_URL,
    }


warnings_step = render_warnings_step

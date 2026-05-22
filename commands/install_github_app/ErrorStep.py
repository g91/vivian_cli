"""ErrorStep — mirrors src/commands/install-github-app/ErrorStep.tsx."""
from __future__ import annotations

from ...constants.github_app import GITHUB_ACTION_SETUP_DOCS_URL


def render_error_step(
    error: str | None,
    error_reason: str | None = None,
    error_instructions: list[str] | None = None,
) -> dict:
    return {
        "title": "Install GitHub App",
        "error": error,
        "reason": error_reason,
        "instructions": error_instructions or [],
        "docs_url": GITHUB_ACTION_SETUP_DOCS_URL,
        "footer": "Press any key to exit",
    }


error_step = render_error_step

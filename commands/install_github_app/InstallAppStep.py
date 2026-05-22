"""InstallAppStep — mirrors src/commands/install-github-app/InstallAppStep.tsx."""
from __future__ import annotations

from ...constants.github_app import GITHUB_ACTION_SETUP_DOCS_URL


def render_install_app_step(repo_url: str) -> dict:
    return {
        "title": "Install the vivian GitHub App",
        "message": "Opening browser to install the vivian GitHub App…",
        "install_url": "https://github.com/apps/vivian",
        "repository_prompt": f"Please install the app for repository: {repo_url}",
        "important_note": "Make sure to grant access to this specific repository",
        "confirm_prompt": "Press Enter once you've installed the app…",
        "docs_url": GITHUB_ACTION_SETUP_DOCS_URL,
    }


install_app_step = render_install_app_step

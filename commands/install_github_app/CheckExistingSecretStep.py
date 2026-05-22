"""CheckExistingSecretStep — mirrors src/commands/install-github-app/CheckExistingSecretStep.tsx."""
from __future__ import annotations

def render_check_existing_secret_step(
    use_existing_secret: bool,
    secret_name: str,
) -> dict:
    return {
        "title": "Install GitHub App",
        "subtitle": "Setup API key secret",
        "warning": "ANTHROPIC_API_KEY already exists in repository secrets!",
        "prompt": "Would you like to:",
        "options": [
            {
                "id": "existing",
                "label": "Use the existing API key",
                "selected": use_existing_secret,
            },
            {
                "id": "new",
                "label": "Create a new secret with a different name",
                "selected": not use_existing_secret,
            },
        ],
        "input": {
            "visible": not use_existing_secret,
            "value": secret_name,
            "placeholder": "e.g., vivian_API_KEY",
            "prompt": "Enter new secret name (alphanumeric with underscores):",
        },
        "navigation_hint": "up/down to select · Enter to continue",
    }


check_existing_secret_step = render_check_existing_secret_step

"""ApiKeyStep — mirrors src/commands/install-github-app/ApiKeyStep.tsx."""
from __future__ import annotations

from typing import Literal


ApiKeySelection = Literal["existing", "new", "oauth"]


def resolve_selected_option(
    existing_api_key: str | None,
    has_oauth_creator: bool,
    selected_option: ApiKeySelection | None = None,
) -> ApiKeySelection:
    if selected_option is not None:
        return selected_option
    if existing_api_key:
        return "existing"
    if has_oauth_creator:
        return "oauth"
    return "new"


def get_previous_option(
    selected_option: ApiKeySelection,
    existing_api_key: str | None,
    has_oauth_creator: bool,
) -> ApiKeySelection:
    if selected_option == "new" and has_oauth_creator:
        return "oauth"
    if selected_option == "oauth" and existing_api_key:
        return "existing"
    return selected_option


def get_next_option(
    selected_option: ApiKeySelection,
    has_oauth_creator: bool,
) -> ApiKeySelection:
    if selected_option == "existing":
        return "oauth" if has_oauth_creator else "new"
    if selected_option == "oauth":
        return "new"
    return selected_option


def render_api_key_step(
    existing_api_key: str | None,
    api_key_or_oauth_token: str,
    has_oauth_creator: bool = False,
    selected_option: ApiKeySelection | None = None,
) -> dict:
    resolved = resolve_selected_option(existing_api_key, has_oauth_creator, selected_option)
    options: list[dict] = []
    if existing_api_key:
        options.append(
            {
                "id": "existing",
                "label": "Use your existing vivian Code API key",
                "selected": resolved == "existing",
            }
        )
    if has_oauth_creator:
        options.append(
            {
                "id": "oauth",
                "label": "Create a long-lived token with your vivian subscription",
                "selected": resolved == "oauth",
            }
        )
    options.append(
        {
            "id": "new",
            "label": "Enter a new API key",
            "selected": resolved == "new",
        }
    )
    return {
        "title": "Install GitHub App",
        "subtitle": "Choose API key",
        "options": options,
        "input": {
            "visible": resolved == "new",
            "value": api_key_or_oauth_token,
            "placeholder": "sk-ant… (Create a new key at https://api-vivian.d0a.net/settings/keys)",
            "masked": True,
        },
        "navigation_hint": "up/down to select · Enter to continue",
        "confirm_action": "create_oauth_token" if resolved == "oauth" else "submit",
    }


api_key_step = render_api_key_step

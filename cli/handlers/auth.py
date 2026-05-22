"""Auth subcommand handler — mirrors src/cli/handlers/auth.ts.

Handles login, logout, token storage and OAuth flow helpers.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path.home() / ".vivian"
_AUTH_FILE = _CONFIG_DIR / "auth.json"


def _load_auth() -> dict:
    try:
        return json.loads(_AUTH_FILE.read_text())
    except Exception:
        return {}


def _save_auth(data: dict) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _AUTH_FILE.write_text(json.dumps(data, indent=2))


def is_logged_in() -> bool:
    """Return True if credentials are stored locally."""
    auth = _load_auth()
    return bool(auth.get("api_key") or auth.get("oauth_token"))


def get_api_key() -> Optional[str]:
    """Return the stored API key (env var takes priority)."""
    return (
        os.environ.get("VIVIAN_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or _load_auth().get("api_key")
    )


def login(api_key: str) -> None:
    """Store *api_key* in the local auth file."""
    auth = _load_auth()
    auth["api_key"] = api_key
    _save_auth(auth)
    print("Logged in successfully.")


def logout(*, clear_onboarding: bool = True) -> None:
    """Remove stored credentials."""
    auth = _load_auth()
    auth.pop("api_key", None)
    auth.pop("oauth_token", None)
    if clear_onboarding:
        auth.pop("onboarding_complete", None)
    _save_auth(auth)
    print("Logged out.")


def install_oauth_tokens(tokens: dict) -> None:
    """Persist OAuth tokens and populate account info."""
    logout(clear_onboarding=False)
    auth = _load_auth()
    auth["oauth_token"] = tokens.get("access_token")
    auth["refresh_token"] = tokens.get("refresh_token")
    if account := tokens.get("account"):
        auth["account_uuid"] = account.get("uuid")
        auth["email"] = account.get("email")
    _save_auth(auth)
    logger.debug("OAuth tokens installed.")


def print_auth_status() -> None:
    """Print current auth status to stdout."""
    key = get_api_key()
    if key:
        masked = key[:8] + "…" + key[-4:] if len(key) > 12 else "***"
        print(f"Authenticated  (key: {masked})")
    else:
        print("Not authenticated — run 'vivian login' or set VIVIAN_API_KEY.")

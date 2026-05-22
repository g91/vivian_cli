"""Integration configuration — central setup that all vivian_cli modules read.

Call `configure(...)` once at startup (app boot or first CLI invocation).
All defaults come from environment variables so zero-config works in Docker.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IntegrationConfig:
    # ── External-facing URLs ──────────────────────────────────────────────
    # The REST API base that CLI clients call. All /v1/* routes live here.
    base_api_url: str = field(
        default_factory=lambda: os.environ.get("VIVIAN_API_BASE_URL", "https://api-vivian.d0a.net")
    )

    # The Vivian web UI / OllamaPlanner. OAuth redirects and session URLs.
    web_url: str = field(
        default_factory=lambda: os.environ.get("VIVIAN_WEB_URL", "https://vivian.d0a.net")
    )

    # ── Internal OllamaPlanner connection (server-side only) ─────────────
    # Where the Flask server is running locally (bypasses Cloudflare/proxy).
    internal_api_url: str = field(
        default_factory=lambda: os.environ.get("VIVIAN_INTERNAL_URL", "http://localhost:5000")
    )

    # ── Auth ──────────────────────────────────────────────────────────────
    # Static API key for machine-to-machine calls (server context).
    api_key: Optional[str] = field(
        default_factory=lambda: os.environ.get("VIVIAN_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    )

    # Admin JWT for elevated operations (set after /api/admin/login).
    admin_jwt: Optional[str] = field(
        default_factory=lambda: os.environ.get("VIVIAN_ADMIN_JWT")
    )

    # OAuth client ID for PKCE flows.
    oauth_client_id: str = field(
        default_factory=lambda: os.environ.get("VIVIAN_OAUTH_CLIENT_ID", "vivian-cli")
    )

    # ── AI Model ─────────────────────────────────────────────────────────
    default_model: str = field(
        default_factory=lambda: os.environ.get("VIVIAN_DEFAULT_MODEL", "qwen3.6")
    )

    max_tokens: int = field(
        default_factory=lambda: int(os.environ.get("VIVIAN_MAX_TOKENS", "4096"))
    )

    # ── Bridge / Remote Control ────────────────────────────────────────────
    # Whether the bridge system is active (enable for remote web control).
    bridge_enabled: bool = field(
        default_factory=lambda: os.environ.get("VIVIAN_BRIDGE_ENABLED", "0") not in ("", "0", "false", "no")
    )

    # ── Misc ──────────────────────────────────────────────────────────────
    debug: bool = field(
        default_factory=lambda: os.environ.get("VIVIAN_DEBUG", "0") not in ("", "0", "false", "no")
    )

    timeout: float = field(
        default_factory=lambda: float(os.environ.get("VIVIAN_TIMEOUT", "600"))
    )


_config: Optional[IntegrationConfig] = None


def configure(**kwargs) -> IntegrationConfig:
    """Set global integration config. Call once at startup.

    Example:
        configure(
            base_api_url="https://api-vivian.d0a.net",
            internal_api_url="http://localhost:5000",
            api_key="viv-...",
            default_model="qwen3.6",
        )
    """
    global _config
    _config = IntegrationConfig(**kwargs)

    # Push values into the oauth constants so all bridge modules pick them up.
    from ..constants.oauth import set_oauth_config
    set_oauth_config({
        "BASE_API_URL": _config.base_api_url,
        "vivian_AI_URL": _config.web_url,
        "CLIENT_ID": _config.oauth_client_id,
        "REDIRECT_URI": f"{_config.web_url}/oauth/callback",
        "TOKEN_URL": f"{_config.base_api_url}/oauth/token",
        "REVOKE_URL": f"{_config.base_api_url}/oauth/revoke",
        "USERINFO_URL": f"{_config.base_api_url}/oauth/userinfo",
        "AUTHORIZE_URL": f"{_config.web_url}/oauth/authorize",
    })

    # Push debug flag.
    if _config.debug:
        from ..utils.debug import enable_debug_mode
        enable_debug_mode()

    return _config


def get_config() -> IntegrationConfig:
    """Return the current config, lazily initializing from env vars if needed."""
    global _config
    if _config is None:
        _config = configure()
    return _config

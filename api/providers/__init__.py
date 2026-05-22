"""Provider abstraction for Vivian CLI.

Exposes helpers for resolving the correct API base_url, api_key, and
auth style from user config, regardless of which AI backend is selected.
"""

from .registry import (
    PROVIDERS,
    resolve_client_config,
    get_provider_info,
    list_providers_text,
)

__all__ = [
    "PROVIDERS",
    "resolve_client_config",
    "get_provider_info",
    "list_providers_text",
]

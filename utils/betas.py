"""Beta header constants and helpers — mirrors src/utils/betas.ts"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

# Known beta headers (from constants/betas.ts)
vivian_CODE_20250219_BETA_HEADER = "vivian-code-20250219"
CLI_INTERNAL_BETA_HEADER = "cli-internal"
CONTEXT_1M_BETA_HEADER = "extended-cache-ttl-2025-04-24"
CONTEXT_MANAGEMENT_BETA_HEADER = "context-management-2025-01-13"
INTERLEAVED_THINKING_BETA_HEADER = "interleaved-thinking-2025-05-14"
PROMPT_CACHING_SCOPE_BETA_HEADER = "prompt-caching-scope-2025-04-24"
REDACT_THINKING_BETA_HEADER = "redacted-thinking-2025-05-14"
STRUCTURED_OUTPUTS_BETA_HEADER = "structured-outputs-2025-06-01"
SUMMARIZE_CONNECTOR_TEXT_BETA_HEADER = "summarize-connector-text-2025-05-14"
TOKEN_EFFICIENT_TOOLS_BETA_HEADER = "token-efficient-tools-2025-02-19"
TOOL_SEARCH_BETA_HEADER_1P = "tool-search-2025-06-01"
TOOL_SEARCH_BETA_HEADER_3P = "tool-search-3p-2025-06-01"
WEB_SEARCH_BETA_HEADER = "web-search-2025-03-05"
OAUTH_BETA_HEADER = "oauth-2025-04-20"

# SDK betas allowed for API-key users
ALLOWED_SDK_BETAS = [CONTEXT_1M_BETA_HEADER]


def should_include_first_party_only_betas() -> bool:
    """Return True when connected to the Anthropic first-party API."""
    # In Python port, default to True for direct API key usage
    _enabled = True
    return _enabled


def get_beta_headers(
    *,
    model: Optional[str] = None,
    api_provider: Optional[str] = None,
    is_interactive: bool = True,
) -> list[str]:
    """Build the list of beta headers to send with API requests."""
    betas: list[str] = []

    if is_interactive:
        betas.append(vivian_CODE_20250219_BETA_HEADER)

    if should_include_first_party_only_betas():
        betas.append(CONTEXT_MANAGEMENT_BETA_HEADER)
        betas.append(PROMPT_CACHING_SCOPE_BETA_HEADER)

    if not os.environ.get("vivian_CODE_DISABLE_PROMPT_CACHING"):
        pass  # Prompt caching is enabled by default

    return betas

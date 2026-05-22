"""API client — mirrors src/services/api/client.ts."""
from __future__ import annotations

import os
from typing import Any, Optional


def getAnthropicClient(
    max_retries: int = 3,
    model: Optional[str] = None,
    source: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    """Get an Anthropic API client.

    Mirrors getAnthropicClient() from client.ts.
    """
    try:
        import anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        base_url = os.environ.get("ANTHROPIC_BASE_URL")

        client_kwargs: dict = {"max_retries": max_retries}
        if api_key:
            client_kwargs["api_key"] = api_key
        if base_url:
            client_kwargs["base_url"] = base_url
        client_kwargs.update(kwargs)

        return anthropic.AsyncAnthropic(**client_kwargs)
    except ImportError:
        raise ImportError(
            "The 'anthropic' package is required. Install with: pip install anthropic"
        )


get_anthropic_client = getAnthropicClient

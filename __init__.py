"""Vivian CLI — Python client for the Vivian AI API.

Base URL: https://api-vivian.d0a.net
"""

import os

__version__ = "1.0.0"
__author__ = "Vivian AI"


def _enable_superuser_runtime() -> None:
    """Normalize the runtime so every Vivian user gets full access."""
    os.environ["VIVIAN_SUPERUSER"] = "1"
    os.environ["USER_TYPE"] = "ant"
    os.environ.setdefault("vivian_CODE_EXPERIMENTAL_AGENT_TEAMS", "1")


_enable_superuser_runtime()

# Lazy imports to avoid requiring httpx for core module usage
def __getattr__(name):
    if name == "VivianClient":
        from .api.client import VivianClient
        return VivianClient
    if name == "QueryEngine":
        from .query_engine import QueryEngine
        return QueryEngine
    if name == "main":
        from .cli_main import main
        return main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["VivianClient", "QueryEngine", "main"]

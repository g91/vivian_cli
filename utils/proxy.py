"""Proxy configuration utilities — mirrors src/utils/proxy.ts"""
from __future__ import annotations

import os
import re
from typing import Optional
from urllib.parse import urlparse


def get_proxy_url(env: dict | None = None) -> Optional[str]:
    """Return the active HTTPS proxy URL if configured."""
    _env = env if env is not None else os.environ
    return (
        _env.get("https_proxy")
        or _env.get("HTTPS_PROXY")
        or _env.get("http_proxy")
        or _env.get("HTTP_PROXY")
    )


def get_no_proxy(env: dict | None = None) -> Optional[str]:
    """Return the NO_PROXY value if set."""
    _env = env if env is not None else os.environ
    return _env.get("no_proxy") or _env.get("NO_PROXY")


def should_bypass_proxy(url_string: str, no_proxy: Optional[str] = None) -> bool:
    """Return True if the URL should bypass the proxy per NO_PROXY rules."""
    if no_proxy is None:
        no_proxy = get_no_proxy()
    if not no_proxy:
        return False
    if no_proxy == "*":
        return True
    try:
        parsed = urlparse(url_string)
        hostname = (parsed.hostname or "").lower()
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        host_with_port = f"{hostname}:{port}"

        patterns = [p.strip() for p in re.split(r"[,\s]+", no_proxy) if p.strip()]
        for pattern in patterns:
            pattern = pattern.lower()
            if ":" in pattern:
                if host_with_port == pattern:
                    return True
            elif pattern.startswith("."):
                suffix = pattern
                if hostname == pattern[1:] or hostname.endswith(suffix):
                    return True
            elif hostname == pattern:
                return True
    except Exception:
        pass
    return False


def disable_keep_alive() -> None:
    """Signal that keep-alive should be disabled (sets env var)."""
    os.environ["vivian_CODE_NO_KEEPALIVE"] = "1"

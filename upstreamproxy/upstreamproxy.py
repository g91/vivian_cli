"""CCR upstreamproxy init — mirrors src/upstreamproxy/upstreamproxy.ts.

Container-side wiring for CCR sessions:
  1. Reads session token from SESSION_TOKEN_PATH
  2. Downloads the upstreamproxy CA cert
  3. Starts local CONNECT→WebSocket relay
  4. Unlinks token file
  5. Exposes HTTPS_PROXY / SSL_CERT_FILE env vars for subprocesses
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .relay import start_upstream_proxy_relay, UpstreamRelay

log = logging.getLogger(__name__)

SESSION_TOKEN_PATH = "/run/ccr/session_token"
SYSTEM_CA_BUNDLE = "/etc/ssl/certs/ca-certificates.crt"

NO_PROXY_LIST = ",".join([
    "localhost",
    "127.0.0.1",
    "::1",
    "169.254.0.0/16",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "api-vivian.d0a.net",
    ".api-vivian.d0a.net",
    "*.api-vivian.d0a.net",
    "github.com",
    "api.github.com",
    "*.github.com",
    "*.githubusercontent.com",
    "registry.npmjs.org",
    "pypi.org",
    "files.pythonhosted.org",
    "index.crates.io",
    "proxy.golang.org",
])


@dataclass
class UpstreamProxyState:
    enabled: bool = False
    port: Optional[int] = None
    ca_bundle_path: Optional[str] = None


_state = UpstreamProxyState()


async def init_upstream_proxy(
    token_path: str = SESSION_TOKEN_PATH,
    system_ca: str = SYSTEM_CA_BUNDLE,
) -> UpstreamProxyState:
    """Initialize upstreamproxy.  Returns state with enabled=False on any error."""
    global _state

    # Only active when vivian_CODE_UPSTREAM_PROXY_WS_URL is set
    ws_url = os.environ.get("vivian_CODE_UPSTREAM_PROXY_WS_URL")
    if not ws_url:
        return _state

    try:
        token_file = Path(token_path)
        if not token_file.exists():
            log.debug("No CCR session token at %s — upstream proxy disabled", token_path)
            return _state

        token = token_file.read_text().strip()
        if not token:
            log.warning("Empty CCR session token — upstream proxy disabled")
            return _state

        # Start relay
        relay = await start_upstream_proxy_relay(ws_url, token)
        port = relay.port

        # Build merged CA bundle
        ca_bundle_path = await _build_ca_bundle(system_ca)

        # Unlink token file (keep token heap-only after relay is confirmed up)
        try:
            token_file.unlink()
        except OSError:
            pass

        # Expose env vars
        proxy_url = f"http://127.0.0.1:{port}"
        os.environ["HTTPS_PROXY"] = proxy_url
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["https_proxy"] = proxy_url
        os.environ["http_proxy"] = proxy_url
        os.environ["NO_PROXY"] = NO_PROXY_LIST
        os.environ["no_proxy"] = NO_PROXY_LIST
        if ca_bundle_path:
            os.environ["SSL_CERT_FILE"] = ca_bundle_path
            os.environ["REQUESTS_CA_BUNDLE"] = ca_bundle_path

        _state = UpstreamProxyState(enabled=True, port=port, ca_bundle_path=ca_bundle_path)
        log.debug("Upstream proxy relay started on port %s", port)
        return _state

    except Exception as exc:
        log.warning("Failed to initialize upstream proxy: %s — continuing without proxy", exc)
        return _state


async def _build_ca_bundle(system_ca: str) -> Optional[str]:
    """Download proxy CA cert and merge with system bundle."""
    proxy_ca_url = os.environ.get("vivian_CODE_UPSTREAM_PROXY_CA_URL")
    if not proxy_ca_url:
        return None
    try:
        import httpx
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(proxy_ca_url, timeout=10)
            resp.raise_for_status()
            proxy_ca = resp.text
        system_pem = ""
        try:
            system_pem = Path(system_ca).read_text()
        except OSError:
            pass
        merged = system_pem.rstrip() + "\n" + proxy_ca.strip() + "\n"
        out_path = Path.home() / ".vivian" / "upstream-proxy-ca.pem"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(merged)
        return str(out_path)
    except Exception as exc:
        log.debug("Failed to build CA bundle: %s", exc)
        return None


def get_upstream_proxy_state() -> UpstreamProxyState:
    return _state

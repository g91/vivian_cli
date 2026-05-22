"""
Port of src/utils/plugins/fetchTelemetry.ts

Telemetry for plugin/marketplace fetches that hit the network.
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from .officialMarketplace import OFFICIAL_MARKETPLACE_NAME


PluginFetchSource = str
PluginFetchOutcome = str

KNOWN_PUBLIC_HOSTS = {
    "github.com", "raw.githubusercontent.com", "objects.githubusercontent.com",
    "gist.githubusercontent.com", "gitlab.com", "bitbucket.org", "codeberg.org",
    "dev.azure.com", "ssh.dev.azure.com", "storage.googleapis.com",
}


def _extract_host(url_or_spec: str) -> str:
    scp_match = re.match(r"^[^@/]+@([^:/]+):", url_or_spec)
    if scp_match:
        host = scp_match.group(1)
    else:
        try:
            host = urlparse(url_or_spec).hostname or "unknown"
        except Exception:
            return "unknown"
    normalized = host.lower()
    return normalized if normalized in KNOWN_PUBLIC_HOSTS else "other"


def _is_official_repo(url_or_spec: str) -> bool:
    return f"anthropics/{OFFICIAL_MARKETPLACE_NAME}" in url_or_spec


def logPluginFetch(
    source: str,
    url_or_spec: Optional[str],
    outcome: str,
    duration_ms: float,
    error_kind: Optional[str] = None,
) -> None:
    try:
        from ...services.analytics import logEvent
        logEvent("tengu_plugin_remote_fetch", {
            "source": source,
            "host": _extract_host(url_or_spec) if url_or_spec else "unknown",
            "is_official": _is_official_repo(url_or_spec) if url_or_spec else False,
            "outcome": outcome,
            "duration_ms": round(duration_ms),
            **(dict(error_kind=error_kind) if error_kind else {}),
        })
    except Exception:
        pass


def classifyFetchError(error) -> str:
    msg = str(getattr(error, "message", error) if hasattr(error, "message") else error)
    if re.search(r"ENOTFOUND|ECONNREFUSED|EAI_AGAIN|Could not resolve host|Connection refused", msg, re.IGNORECASE):
        return "dns_or_refused"
    if re.search(r"ETIMEDOUT|timed out|timeout", msg, re.IGNORECASE):
        return "timeout"
    if re.search(r"ECONNRESET|socket hang up|Connection reset by peer|remote end hung up", msg, re.IGNORECASE):
        return "conn_reset"
    if re.search(r"403|401|authentication|permission denied", msg, re.IGNORECASE):
        return "auth"
    if re.search(r"404|not found|repository not found", msg, re.IGNORECASE):
        return "not_found"
    if re.search(r"certificate|SSL|TLS|unable to get local issuer", msg, re.IGNORECASE):
        return "tls"
    if re.search(r"Invalid response format|Invalid marketplace schema", msg, re.IGNORECASE):
        return "invalid_schema"
    return "other"


# Aliases for camelCase consumers
extractHost = _extract_host
isOfficialRepo = _is_official_repo


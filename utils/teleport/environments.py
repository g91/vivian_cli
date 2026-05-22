"""
Port of src/utils/teleport/environments.ts

Fetch and manage Teleport environment resources via the Anthropic API.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from .api import getOAuthHeaders, _get_base_api_url, _get_oauth_tokens, _get_organization_uuid  # type: ignore

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

EnvironmentKind = str   # 'anthropic_cloud' | 'byoc' | 'bridge'
EnvironmentState = str  # 'active'

EnvironmentResource = Dict[str, Any]
EnvironmentListResponse = Dict[str, Any]


# ---------------------------------------------------------------------------
# Fetch environments
# ---------------------------------------------------------------------------

async def fetchEnvironments() -> List[EnvironmentResource]:
    """Fetch the list of available environments from the Environment API."""
    tokens = _get_oauth_tokens()
    access_token = (tokens or {}).get("accessToken")
    if not access_token:
        raise RuntimeError(
            "vivian Code web sessions require authentication with a api-vivian.d0a.net account. "
            "API key authentication is not sufficient. "
            "Please run /login to authenticate, or check your authentication status with /status."
        )

    org_uuid = await _get_organization_uuid()
    if not org_uuid:
        raise RuntimeError("Unable to get organization UUID")

    url = f"{_get_base_api_url()}/v1/environment_providers"
    headers = {
        **getOAuthHeaders(access_token),
        "x-organization-uuid": org_uuid,
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15.0)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch environments: {resp.status_code} {resp.reason}"
            )
        data: EnvironmentListResponse = resp.json()
        return data.get("environments", [])
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to fetch environments: {exc}") from exc


# ---------------------------------------------------------------------------
# Create default environment
# ---------------------------------------------------------------------------

async def createDefaultCloudEnvironment(name: str) -> EnvironmentResource:
    """Create a default ``anthropic_cloud`` environment for users who have none."""
    tokens = _get_oauth_tokens()
    access_token = (tokens or {}).get("accessToken")
    if not access_token:
        raise RuntimeError("No access token available")

    org_uuid = await _get_organization_uuid()
    if not org_uuid:
        raise RuntimeError("Unable to get organization UUID")

    url = f"{_get_base_api_url()}/v1/environment_providers/cloud/create"
    headers = {
        **getOAuthHeaders(access_token),
        "anthropic-beta": "ccr-byoc-2025-07-29",
        "x-organization-uuid": org_uuid,
    }
    payload = {
        "name": name,
        "kind": "anthropic_cloud",
        "description": "",
        "config": {
            "environment_type": "anthropic",
            "cwd": "/home/user",
            "init_script": None,
            "environment": {},
            "languages": [
                {"name": "python", "version": "3.11"},
                {"name": "node", "version": "20"},
            ],
            "network_config": {
                "allowed_hosts": [],
                "allow_default_hosts": True,
            },
        },
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=15.0)
    resp.raise_for_status()
    return resp.json()

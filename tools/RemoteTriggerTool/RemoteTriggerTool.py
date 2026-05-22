"""RemoteTriggerTool — mirrors src/tools/RemoteTriggerTool/RemoteTriggerTool.tsx"""
from __future__ import annotations
from typing import Any, Dict

import json

import httpx

from ...constants.oauth import get_oauth_config
from ...services.oauth.client import get_organization_uuid
from ...utils.auth import check_and_refresh_oauth_token_if_needed, get_vivian_ai_oauth_tokens

TOOL_NAME = "RemoteTrigger"

_TRIGGERS_BETA = "ccr-triggers-2026-01-30"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["action"],
    "properties": {
        "action": {"type": "string", "enum": ["list", "get", "create", "update", "run"]},
        "trigger_id": {"type": "string", "description": "Trigger id for get, update, or run"},
        "body": {"type": "object", "description": "JSON body for create or update"},
    },
}


async def description() -> str:
    return "Manage remote triggers for authenticated vivian Code sessions."


async def prompt() -> str:
    return "Use this tool to list, inspect, create, update, or run remote triggers."


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    await check_and_refresh_oauth_token_if_needed()
    tokens = get_vivian_ai_oauth_tokens()
    access_token = getattr(tokens, "access_token", None)
    if not access_token:
        raise RuntimeError("Not authenticated with a api-vivian.d0a.net account. Run /login and try again.")

    organization_uuid = await get_organization_uuid()
    if not organization_uuid:
        raise RuntimeError("Unable to resolve organization UUID.")

    base_url = f"{get_oauth_config()['BASE_API_URL']}/v1/code/triggers"
    action = input_data.get("action")
    trigger_id = input_data.get("trigger_id")
    body = input_data.get("body")

    method = "GET"
    request_url = base_url
    request_body: Any = None

    if action == "get":
        if not trigger_id:
            raise ValueError("get requires trigger_id")
        request_url = f"{base_url}/{trigger_id}"
    elif action == "create":
        if body is None:
            raise ValueError("create requires body")
        method = "POST"
        request_body = body
    elif action == "update":
        if not trigger_id:
            raise ValueError("update requires trigger_id")
        if body is None:
            raise ValueError("update requires body")
        method = "POST"
        request_url = f"{base_url}/{trigger_id}"
        request_body = body
    elif action == "run":
        if not trigger_id:
            raise ValueError("run requires trigger_id")
        method = "POST"
        request_url = f"{base_url}/{trigger_id}/run"
        request_body = {}
    elif action != "list":
        raise ValueError(f"Unsupported action '{action}'")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
        "anthropic-beta": _TRIGGERS_BETA,
        "x-organization-uuid": organization_uuid,
    }

    timeout = 20.0
    abort_controller = context.get("abortController") if isinstance(context, dict) else None
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(
            method,
            request_url,
            headers=headers,
            json=request_body,
        )

    try:
        parsed = response.json()
    except ValueError:
        parsed = response.text

    return {
        "status": response.status_code,
        "json": json.dumps(parsed, ensure_ascii=True, default=str),
    }

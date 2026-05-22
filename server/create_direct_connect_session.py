"""Create direct-connect session — mirrors src/server/createDirectConnectSession.ts.

Posts to ${serverUrl}/sessions and returns a DirectConnectConfig.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Optional

from .types import parse_connect_response


class DirectConnectError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.name = "DirectConnectError"


def create_direct_connect_session(
    *,
    server_url: str,
    auth_token: Optional[str] = None,
    cwd: str,
    dangerously_skip_permissions: bool = False,
) -> dict:
    headers = {"content-type": "application/json"}
    if auth_token:
        headers["authorization"] = f"Bearer {auth_token}"

    body: dict = {"cwd": cwd}
    if dangerously_skip_permissions:
        body["dangerously_skip_permissions"] = True

    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{server_url}/sessions",
        data=data,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise DirectConnectError(f"Failed to create session: {e.code} {e.reason}") from e
    except Exception as exc:
        raise DirectConnectError(f"Failed to connect to server at {server_url}: {exc}") from exc

    try:
        data_obj = parse_connect_response(raw)
    except Exception as exc:
        raise DirectConnectError(f"Invalid session response: {exc}") from exc

    config = {
        "server_url": server_url,
        "session_id": data_obj.session_id,
        "ws_url": data_obj.ws_url,
        "auth_token": auth_token,
    }
    return {"config": config, "work_dir": data_obj.work_dir}

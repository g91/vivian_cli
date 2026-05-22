"""Swarm permission poller — mirrors src/hooks/useSwarmPermissionPoller.ts."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..utils.swarm.permissionSync import isSwarmWorker, pollForResponse, removeWorkerResponse


LOGGER = logging.getLogger(__name__)
POLL_INTERVAL_MS = 500
pendingCallbacks: dict[str, dict[str, Any]] = {}
pendingSandboxCallbacks: dict[str, dict[str, Any]] = {}


def registerPermissionCallback(callback: dict[str, Any]) -> None:
    pendingCallbacks[callback["requestId"]] = callback


def unregisterPermissionCallback(requestId: str) -> None:
    pendingCallbacks.pop(requestId, None)


def hasPermissionCallback(requestId: str) -> bool:
    return requestId in pendingCallbacks


def clearAllPendingCallbacks() -> None:
    pendingCallbacks.clear()
    pendingSandboxCallbacks.clear()


def processMailboxPermissionResponse(params: dict[str, Any]) -> bool:
    callback = pendingCallbacks.pop(params["requestId"], None)
    if callback is None:
        return False

    if params.get("decision") == "approved":
        callback["onAllow"](
            params.get("updatedInput"),
            params.get("permissionUpdates") or [],
            params.get("feedback"),
        )
    else:
        callback["onReject"](params.get("feedback"))
    return True


def registerSandboxPermissionCallback(callback: dict[str, Any]) -> None:
    pendingSandboxCallbacks[callback["requestId"]] = callback


def hasSandboxPermissionCallback(requestId: str) -> bool:
    return requestId in pendingSandboxCallbacks


def processSandboxPermissionResponse(params: dict[str, Any]) -> bool:
    callback = pendingSandboxCallbacks.pop(params["requestId"], None)
    if callback is None:
        return False
    callback["resolve"](bool(params.get("allow")))
    return True


def processResponse(response: dict[str, Any]) -> bool:
    return processMailboxPermissionResponse(response)


async def useSwarmPermissionPoller() -> dict[str, Any]:
    """Poll resolved swarm permission requests and dispatch registered callbacks."""
    if not isSwarmWorker():
        return {"polling": False, "pendingRequests": 0}

    async def poll_once() -> int:
        processed = 0
        for request_id in list(pendingCallbacks):
            try:
                response = await pollForResponse(request_id)
            except Exception as error:
                LOGGER.warning("failed to poll swarm permission response for %s: %s", request_id, error)
                continue

            if not response:
                continue

            if processResponse(response):
                processed += 1
                try:
                    await removeWorkerResponse(request_id)
                except Exception as error:
                    LOGGER.warning("failed to remove processed worker response for %s: %s", request_id, error)

        return processed

    return {
        "polling": True,
        "pendingRequests": len(pendingCallbacks),
        "pollIntervalMs": POLL_INTERVAL_MS,
        "pollOnce": poll_once,
    }


use_swarm_permission_poller = useSwarmPermissionPoller
register_permission_callback = registerPermissionCallback
unregister_permission_callback = unregisterPermissionCallback
has_permission_callback = hasPermissionCallback
clear_all_pending_callbacks = clearAllPendingCallbacks
process_mailbox_permission_response = processMailboxPermissionResponse
register_sandbox_permission_callback = registerSandboxPermissionCallback
has_sandbox_permission_callback = hasSandboxPermissionCallback
process_sandbox_permission_response = processSandboxPermissionResponse

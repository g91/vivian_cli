"""Swarm worker permission handler — mirrors src/hooks/toolPermission/handlers/swarmWorkerHandler.ts."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from ...useSwarmPermissionPoller import registerPermissionCallback
from ....utils.swarm.permissionSync import createPermissionRequest, isSwarmWorker, sendPermissionRequestViaMailbox


LOGGER = logging.getLogger(__name__)
SwarmWorkerPermissionParams = dict[str, Any]


async def handleSwarmWorkerPermission(
    params: SwarmWorkerPermissionParams,
) -> dict[str, Any] | None:
    """Forward worker permission requests to the swarm leader when applicable."""
    if not isSwarmWorker():
        return None

    ctx = params["ctx"]
    description = params.get("description", "")
    updated_input = params.get("updatedInput")
    suggestions = params.get("suggestions")

    classifier = getattr(ctx, "tryClassifier", None)
    if callable(classifier):
        classifier_result = await classifier(params.get("pendingClassifierCheck"), updated_input)
        if classifier_result is not None:
            return classifier_result

    try:
        request = createPermissionRequest(
            {
                "toolName": getattr(getattr(ctx, "tool", None), "name", None)
                or getattr(ctx, "tool", {}).get("name", "unknown"),
                "toolUseId": getattr(ctx, "toolUseID", ""),
                "input": getattr(ctx, "input", {}),
                "description": description,
                "permissionSuggestions": suggestions or [],
            }
        )
    except Exception as error:
        LOGGER.warning("failed to create swarm permission request: %s", error)
        return None

    loop = asyncio.get_running_loop()
    future: asyncio.Future[dict[str, Any]] = loop.create_future()

    registerPermissionCallback(
        {
            "requestId": request["id"],
            "toolUseId": getattr(ctx, "toolUseID", ""),
            "onAllow": lambda allowed_input, permission_updates, feedback=None: asyncio.create_task(
                _resolve_allow(ctx, future, allowed_input, permission_updates, feedback)
            ),
            "onReject": lambda feedback=None: _resolve_reject(ctx, future, feedback),
        }
    )

    set_app_state = getattr(getattr(ctx, "toolUseContext", None), "setAppState", None)
    if callable(set_app_state):
        set_app_state(
            lambda prev: {
                **prev,
                "pendingWorkerRequest": {
                    "toolName": request["toolName"],
                    "toolUseId": request["toolUseId"],
                    "description": description,
                },
            }
        )

    await sendPermissionRequestViaMailbox(request)
    return await future


async def _resolve_allow(
    ctx: Any,
    future: asyncio.Future[dict[str, Any]],
    allowed_input: dict[str, Any] | None,
    permission_updates: list[dict[str, Any]],
    feedback: str | None,
) -> None:
    if future.done():
        return
    final_input = allowed_input if allowed_input else getattr(ctx, "input", {})
    future.set_result(await ctx.handleUserAllow(final_input, permission_updates, feedback))


def _resolve_reject(ctx: Any, future: asyncio.Future[dict[str, Any]], feedback: str | None) -> None:
    if future.done():
        return
    ctx.logDecision(
        {"decision": "reject", "source": {"type": "user_reject", "hasFeedback": bool(feedback)}},
    )
    future.set_result(ctx.cancelAndAbort(feedback))


async def swarmWorkerHandler(toolName: str, args: dict[str, Any]) -> bool:
    """Backward-compatible boolean wrapper around swarm worker permission handling."""
    decision = await handleSwarmWorkerPermission(args)
    return decision is None or decision.get("behavior") != "deny"


swarmWorkerHandler = handleSwarmWorkerPermission
swarm_worker_handler = swarmWorkerHandler

"""Interactive permission handler — mirrors src/hooks/toolPermission/handlers/interactiveHandler.ts."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from ..PermissionContext import createResolveOnce


LOGGER = logging.getLogger(__name__)
InteractivePermissionParams = dict[str, Any]


def handleInteractivePermission(
    params: InteractivePermissionParams,
    resolve: Callable[[dict[str, Any]], None],
) -> None:
    """Set up the interactive permission flow and race it with automated approvals."""
    ctx = params["ctx"]
    result = params["result"]
    description = params.get("description", "")
    await_automated = bool(params.get("awaitAutomatedChecksBeforeDialog"))
    resolve_once = createResolveOnce(resolve)

    if ctx.resolveIfAborted(resolve_once.resolve):
        return

    async def _automated_checks() -> None:
        if not await_automated or resolve_once.isResolved():
            return
        try:
            permission_mode = params.get("permissionMode")
            suggestions = result.get("suggestions") if isinstance(result, dict) else None
            updated_input = result.get("updatedInput") if isinstance(result, dict) else None
            hook_result = await ctx.runHooks(permission_mode, suggestions, updated_input)
            if hook_result is not None and resolve_once.claim():
                ctx.removeFromQueue()
                resolve_once.resolve(hook_result)
                return

            classifier = getattr(ctx, "tryClassifier", None)
            if callable(classifier):
                classifier_result = await classifier(result.get("pendingClassifierCheck"), updated_input)
                if classifier_result is not None and resolve_once.claim():
                    ctx.removeFromQueue()
                    resolve_once.resolve(classifier_result)
        except Exception as error:
            LOGGER.warning("interactive automated permission checks failed: %s", error)

    queue_item = {
        "assistantMessage": getattr(ctx, "assistantMessage", None),
        "tool": getattr(ctx, "tool", None),
        "description": description,
        "input": result.get("updatedInput") or getattr(ctx, "input", {}),
        "toolUseContext": getattr(ctx, "toolUseContext", None),
        "toolUseID": getattr(ctx, "toolUseID", ""),
        "permissionResult": result,
    }
    ctx.pushToQueue(queue_item)

    if await_automated:
        asyncio.create_task(_automated_checks())
        return

    if resolve_once.claim():
        resolve_once.resolve(result)


async def interactiveHandler(toolName: str, args: dict[str, Any]) -> bool:
    """Backward-compatible boolean wrapper around the interactive permission flow."""
    future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
    handleInteractivePermission(args, future.set_result)
    decision = await future
    return decision.get("behavior") != "deny"


interactiveHandler = handleInteractivePermission
interactive_handler = interactiveHandler

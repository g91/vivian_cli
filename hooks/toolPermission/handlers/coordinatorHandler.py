"""Coordinator permission handler — mirrors src/hooks/toolPermission/handlers/coordinatorHandler.ts."""
from __future__ import annotations

import logging
from typing import Any


LOGGER = logging.getLogger(__name__)
CoordinatorPermissionParams = dict[str, Any]


async def handleCoordinatorPermission(
    params: CoordinatorPermissionParams,
) -> dict[str, Any] | None:
    """Run automated permission checks before falling back to interactive approval."""
    ctx = params["ctx"]
    updated_input = params.get("updatedInput")
    suggestions = params.get("suggestions")
    permission_mode = params.get("permissionMode")

    try:
        hook_result = await ctx.runHooks(permission_mode, suggestions, updated_input)
        if hook_result is not None:
            return hook_result

        classifier = getattr(ctx, "tryClassifier", None)
        if callable(classifier):
            classifier_result = await classifier(params.get("pendingClassifierCheck"), updated_input)
            if classifier_result is not None:
                return classifier_result
    except Exception as error:
        LOGGER.warning("automated permission check failed: %s", error)

    return None


coordinatorHandler = handleCoordinatorPermission
coordinator_handler = handleCoordinatorPermission

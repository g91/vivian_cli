"""Init entrypoint — mirrors src/entrypoints/init.ts."""
from __future__ import annotations

import asyncio


async def init() -> None:
    """Initialize the Vivian CLI environment."""
    from ..utils.config import enableConfigs, recordFirstStartTime
    from ..services.oauth.client import populateOAuthAccountInfoIfNeeded
    from ..services.remoteManagedSettings.index import (
        initializeRemoteManagedSettingsLoadingPromise,
        loadRemoteManagedSettings,
    )
    from ..utils.apiPreconnect import preconnectAnthropicApi
    from ..utils.debug import logForDebugging

    enableConfigs()
    recordFirstStartTime()
    initializeRemoteManagedSettingsLoadingPromise()

    def _spawn_background(coro, label: str) -> None:
        try:
            asyncio.create_task(coro)
        except Exception as error:
            logForDebugging(f"[init] failed to start {label}: {error}")

    # Start remote managed settings load in the background.
    # Fail-open: startup continues even if this task errors.
    _spawn_background(loadRemoteManagedSettings(), "remote managed settings load")

    # Preconnect in background
    _spawn_background(preconnectAnthropicApi(), "API preconnect")

    # Populate OAuth account info
    try:
        await populateOAuthAccountInfoIfNeeded()
    except Exception as error:
        logForDebugging(f"[init] populateOAuthAccountInfoIfNeeded failed: {error}")

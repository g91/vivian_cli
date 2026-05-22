"""
Port of src/utils/teleport/environmentSelection.ts
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .environments import fetchEnvironments, EnvironmentResource

EnvironmentSelectionInfo = Dict[str, Any]

# Setting source priority order (lowest to highest)
SETTING_SOURCES = ["default", "project", "global", "enterprise", "flagSettings"]


async def getEnvironmentSelectionInfo() -> EnvironmentSelectionInfo:
    """Return info about available environments and which one is selected.

    Gets the available environments from the API, then determines which one
    would be used based on the user's settings (``remote.defaultEnvironmentId``).

    Returns a dict with:
    - ``availableEnvironments``: all environments from the API
    - ``selectedEnvironment``: the environment that would be used, or None
    - ``selectedEnvironmentSource``: the settings source where the default is
      configured, or None if using the first available environment
    """
    environments: List[EnvironmentResource] = await fetchEnvironments()

    if not environments:
        return {
            "availableEnvironments": [],
            "selectedEnvironment": None,
            "selectedEnvironmentSource": None,
        }

    # Try to read the merged settings for defaultEnvironmentId
    default_environment_id: Optional[str] = None
    try:
        from vivian_cli.utils.settings.settings import getSettings_DEPRECATED  # type: ignore
        merged = getSettings_DEPRECATED()
        default_environment_id = (
            (merged or {}).get("remote", {}) or {}
        ).get("defaultEnvironmentId")
    except (ImportError, Exception):
        pass

    # Default: first non-bridge environment, falling back to environments[0]
    selected_environment: EnvironmentResource = next(
        (env for env in environments if env.get("kind") != "bridge"),
        environments[0],
    )
    selected_environment_source: Optional[str] = None

    if default_environment_id:
        matching = next(
            (env for env in environments if env.get("environment_id") == default_environment_id),
            None,
        )
        if matching:
            selected_environment = matching

            # Find which source has this setting (highest priority wins)
            try:
                from vivian_cli.utils.settings.settings import getSettingsForSource  # type: ignore
                for source in reversed(SETTING_SOURCES):
                    if source == "flagSettings":
                        continue
                    src_settings = getSettingsForSource(source) or {}
                    if (
                        src_settings.get("remote", {}) or {}
                    ).get("defaultEnvironmentId") == default_environment_id:
                        selected_environment_source = source
                        break
            except (ImportError, Exception):
                pass

    return {
        "availableEnvironments": environments,
        "selectedEnvironment": selected_environment,
        "selectedEnvironmentSource": selected_environment_source,
    }

"""
Port of src/utils/plugins/hintRecommendation.ts

Plugin-hint recommendations triggered by CLI/SDK hint tags.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from ..config import getGlobalConfig, saveGlobalConfig
from ..debug import logForDebugging
from .installedPluginsManager import isPluginInstalled
from .marketplaceManager import getPluginById
from .pluginIdentifier import isOfficialMarketplaceName, parsePluginIdentifier
from .pluginPolicy import isPluginBlockedByPolicy

MAX_SHOWN_PLUGINS = 100
_tried_this_session: Set[str] = set()

PluginHintRecommendation = Dict[str, Any]


def maybeRecordPluginHint(hint: Dict[str, Any]) -> None:
    """Pre-store gate called by shell tools when a type='plugin' hint is detected."""
    try:
        from ...services.analytics.growthbook import getFeatureValue_CACHED_MAY_BE_STALE
        if not getFeatureValue_CACHED_MAY_BE_STALE("tengu_lapis_finch", False):
            return
    except Exception:
        return

    state = getGlobalConfig().get("vivianCodeHints", {})
    if state.get("disabled"):
        return

    shown: List[str] = state.get("plugin", [])
    if len(shown) >= MAX_SHOWN_PLUGINS:
        return

    plugin_id = hint.get("value", "")
    parsed = parsePluginIdentifier(plugin_id)
    name = parsed.get("name", "")
    marketplace = parsed.get("marketplace", "")
    if not name or not marketplace:
        return
    if not isOfficialMarketplaceName(marketplace):
        return
    if plugin_id in shown:
        return
    if isPluginInstalled(plugin_id):
        return
    if isPluginBlockedByPolicy(plugin_id):
        return
    if plugin_id in _tried_this_session:
        return
    _tried_this_session.add(plugin_id)


def _resetHintRecommendationForTesting() -> None:
    _tried_this_session.clear()


async def resolvePluginHint(hint: Dict[str, Any]) -> Optional[PluginHintRecommendation]:
    """Resolve the pending hint to a renderable recommendation."""
    plugin_id = hint.get("value", "")
    parsed = parsePluginIdentifier(plugin_id)
    name = parsed.get("name", "")
    marketplace = parsed.get("marketplace", "")

    plugin_data = await getPluginById(plugin_id)
    if not plugin_data:
        logForDebugging(f"[hintRecommendation] {plugin_id} not found in marketplace cache")
        return None

    return {
        "pluginId": plugin_id,
        "pluginName": plugin_data.get("entry", {}).get("name", name),
        "marketplaceName": marketplace or "",
        "pluginDescription": plugin_data.get("entry", {}).get("description"),
        "sourceCommand": hint.get("sourceCommand", ""),
    }


def markHintPluginShown(plugin_id: str) -> None:
    """Record that a prompt for this plugin was surfaced."""
    def _update(current: Dict[str, Any]) -> Dict[str, Any]:
        existing = current.get("vivianCodeHints", {}).get("plugin", [])
        if plugin_id in existing:
            return current
        return {
            **current,
            "vivianCodeHints": {
                **current.get("vivianCodeHints", {}),
                "plugin": [*existing, plugin_id],
            },
        }
    saveGlobalConfig(_update)


def disableHintRecommendations() -> None:
    """Called when the user picks 'don't show plugin installation hints again'."""
    def _update(current: Dict[str, Any]) -> Dict[str, Any]:
        if current.get("vivianCodeHints", {}).get("disabled"):
            return current
        return {
            **current,
            "vivianCodeHints": {**current.get("vivianCodeHints", {}), "disabled": True},
        }
    saveGlobalConfig(_update)

"""
Port of src/utils/plugins/marketplaceHelpers.ts

Marketplace loading and formatting helpers. Core functions (load, format, display)
are implemented. Policy/security functions (allowlist, blocklist, host matching)
require the full settings infrastructure and are documented stubs.
"""
from __future__ import annotations

from typing import Any, Optional, List, Dict

import asyncio


EmptyMarketplaceReason = Any


def formatFailureDetails(
    failures: List[Dict[str, str]],
    include_reasons: bool,
) -> str:
    """Format plugin failure details for user display.
    
    Args:
        failures: List of dicts with 'name' and optionally 'reason'/'error' keys.
        include_reasons: Whether to include failure reasons.
    
    Returns:
        Formatted string like "plugin-a (reason); plugin-b (reason)" or "plugin-a, plugin-b".
    """
    max_show = 2
    details_parts: List[str] = []
    for f in failures[:max_show]:
        reason = f.get("reason") or f.get("error") or "unknown error"
        details_parts.append(f"{f['name']} ({reason})" if include_reasons else f["name"])
    
    separator = "; " if include_reasons else ", "
    details = separator.join(details_parts)
    
    remaining = len(failures) - max_show
    more_text = f" and {remaining} more" if remaining > 0 else ""
    
    return f"{details}{more_text}"


def getMarketplaceSourceDisplay(source: Dict[str, Any]) -> str:
    """Extract source display string from marketplace configuration."""
    source_type = source.get("source", "")
    if source_type == "github":
        return source.get("repo", "unknown")
    elif source_type in ("url", "git"):
        return source.get("url", "unknown")
    elif source_type in ("directory", "file"):
        return source.get("path", "unknown")
    elif source_type == "settings":
        return f"settings:{source.get('name', 'unknown')}"
    return "Unknown source"


def createPluginId(plugin_name: str, marketplace_name: str) -> str:
    """Create a plugin ID from plugin name and marketplace name."""
    return f"{plugin_name}@{marketplace_name}"


async def loadMarketplacesWithGracefulDegradation(
    config: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Load marketplaces with graceful degradation for individual failures.
    
    Returns a dict of marketplace_name -> marketplace_data, or None if no
    marketplaces could be loaded. Individual failures are logged but don't
    block other marketplaces.
    """
    if not config:
        return None
    
    result: Dict[str, Any] = {}
    failures: List[Dict[str, str]] = []
    
    for name, marketplace_config in config.items():
        if not isinstance(marketplace_config, dict):
            continue
        try:
            # Try to load marketplace data from the configured source
            source = marketplace_config.get("source", {})
            if isinstance(source, dict):
                source_type = source.get("source", "")
                if source_type == "directory" and source.get("path"):
                    import json, os
                    mp_path = source["path"]
                    # Check common marketplace.json locations
                    for candidate in [
                        os.path.join(mp_path, ".vivian-plugin", "marketplace.json"),
                        os.path.join(mp_path, "marketplace.json"),
                    ]:
                        if os.path.isfile(candidate):
                            with open(candidate, "r") as f:
                                data = json.load(f)
                            if isinstance(data, dict):
                                result[name] = data
                            break
                elif source_type == "github":
                    result[name] = {"name": name, "source": source, "plugins": {}}
                elif source_type == "url":
                    result[name] = {"name": name, "source": source, "plugins": {}}
        except Exception as e:
            failures.append({"name": name, "error": str(e)})
    
    if failures:
        try:
            from ...utils.debug import log_for_debugging
            log_for_debugging(
                f"[marketplace] {len(failures)} marketplace(s) failed to load: "
                f"{formatFailureDetails(failures, include_reasons=True)}"
            )
        except Exception:
            pass
    
    return result if result else None


def formatMarketplaceLoadingErrors(
    failures: List[Dict[str, str]],
    success_count: int,
) -> Optional[Dict[str, str]]:
    """Format marketplace loading failures into appropriate user messages.
    
    Returns a dict with 'type' ('warning' or 'error') and 'message', or None.
    """
    if not failures:
        return None
    
    if success_count > 0:
        if len(failures) == 1:
            msg = f"Warning: Failed to load marketplace '{failures[0]['name']}': {failures[0].get('error', 'unknown')}"
        else:
            msg = f"Warning: Failed to load {len(failures)} marketplaces: {formatFailureNames(failures)}"
        return {"type": "warning", "message": msg}
    
    return {
        "type": "error",
        "message": f"Failed to load all marketplaces. Errors: {formatFailureErrors(failures)}",
    }


def formatFailureNames(failures: List[Dict[str, str]]) -> str:
    """Format failure names as comma-separated list."""
    return ", ".join(f["name"] for f in failures)


def formatFailureErrors(failures: List[Dict[str, str]]) -> str:
    """Format failure errors as semicolon-separated list."""
    return "; ".join(f"{f['name']}: {f.get('error', 'unknown')}" for f in failures)


# ── Policy / security functions (require full settings infrastructure) ──────

def getStrictKnownMarketplaces() -> Optional[List[Dict[str, Any]]]:
    """Get the strict marketplace source allowlist from policy settings.
    
    Stub: requires full policy settings infrastructure.
    """
    return None


def getBlockedMarketplaces() -> Optional[List[Dict[str, Any]]]:
    """Get the marketplace source blocklist from policy settings.
    
    Stub: requires full policy settings infrastructure.
    """
    return None


def getPluginTrustMessage() -> Optional[str]:
    """Get the custom plugin trust message from policy settings.
    
    Stub: requires full policy settings infrastructure.
    """
    return None


def areSourcesEqual(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """Compare two MarketplaceSource objects for equality.
    
    Stub: requires full marketplace source schema infrastructure.
    """
    if a.get("source") != b.get("source"):
        return False
    source_type = a.get("source", "")
    if source_type == "url":
        return a.get("url") == b.get("url")
    if source_type == "github":
        return a.get("repo") == b.get("repo")
    if source_type in ("git",):
        return a.get("url") == b.get("url")
    if source_type in ("file", "directory"):
        return a.get("path") == b.get("path")
    return False


def extractHostFromSource(source: Dict[str, Any]) -> Optional[str]:
    """Extract the host/domain from a marketplace source.
    
    Stub: requires full URL parsing infrastructure.
    """
    source_type = source.get("source", "")
    if source_type == "github":
        return "github.com"
    if source_type in ("git", "url"):
        url = source.get("url", "")
        try:
            from urllib.parse import urlparse
            return urlparse(url).hostname
        except Exception:
            return None
    return None


def isSourceAllowedByPolicy(source: Dict[str, Any]) -> bool:
    strict = getStrictKnownMarketplaces()
    blocked = getBlockedMarketplaces() or []

    if any(areSourcesEqual(source, blocked_source) for blocked_source in blocked):
        return False
    if strict:
        return any(areSourcesEqual(source, allowed_source) for allowed_source in strict)
    return True


def doesSourceMatchHostPattern(source: Dict[str, Any], pattern: Dict[str, Any]) -> bool:
    """Check if a source matches a hostPattern entry.
    
    Stub: requires full policy settings infrastructure.
    """
    return False


def doesSourceMatchPathPattern(source: Dict[str, Any], pattern: Dict[str, Any]) -> bool:
    """Check if a source matches a pathPattern entry.
    
    Stub: requires full policy settings infrastructure.
    """
    return False


def getHostPatternsFromAllowlist() -> Optional[List[str]]:
    """Get hosts from hostPattern entries in the allowlist.
    
    Stub: requires full policy settings infrastructure.
    """
    return None


def extractGitHubRepoFromGitUrl(url: str) -> Optional[str]:
    """Extract GitHub owner/repo from a git URL if it's a GitHub URL."""
    if not url:
        return None
    import re
    # Match github.com URLs: https://github.com/owner/repo or git@github.com:owner/repo
    m = re.match(r"(?:https?://|git@)github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    if m:
        return m.group(1)
    return None


def blockedConstraintMatches(blocked_value: Any, source_value: Any) -> bool:
    """Check if a blocked ref/path constraint matches a source.
    
    Stub: requires full policy settings infrastructure.
    """
    return False


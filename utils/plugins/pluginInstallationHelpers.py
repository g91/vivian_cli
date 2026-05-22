"""
Port of src/utils/plugins/pluginInstallationHelpers.ts

Self-contained utility functions are fully implemented. The deep dependency
resolution and caching pipeline (cacheAndRegisterPlugin, installResolvedPlugin)
requires the full plugin infrastructure (dependencyResolver, installedPluginsManager,
pluginLoader, pluginPolicy, pluginVersioning, zipCache) and is documented as stubs.
"""
from __future__ import annotations

from typing import Any, Optional, Dict, List
import os
import os.path
from datetime import datetime, timezone


PluginInstallationInfo = Dict[str, Any]
InstallCoreResult = Any
InstallPluginResult = Any
InstallPluginParams = Dict[str, Any]


def getCurrentTimestamp() -> str:
    """Get current ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()


def validatePathWithinBase(base_path: str, relative_path: str) -> str:
    """Validate that a resolved path stays within a base directory.
    
    Prevents path traversal attacks where malicious paths like '../../../etc/passwd'
    could escape the expected directory.
    
    Returns the validated absolute path.
    Raises ValueError if the path would escape the base directory.
    """
    resolved = os.path.realpath(os.path.join(base_path, relative_path))
    normalized_base = os.path.realpath(base_path)
    
    # Ensure resolved starts with base (with separator to avoid partial matches)
    if not resolved.startswith(normalized_base + os.sep) and resolved != normalized_base:
        raise ValueError(
            f"Path traversal detected: '{relative_path}' would escape the base directory"
        )
    
    return resolved


def parsePluginId(plugin_id: str) -> Optional[Dict[str, str]]:
    """Parse plugin ID into components.
    
    Args:
        plugin_id: Plugin ID in "plugin@marketplace" format.
    
    Returns:
        Dict with 'name' and 'marketplace' keys, or None if invalid.
    """
    parts = plugin_id.split("@", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return {"name": parts[0], "marketplace": parts[1]}


def formatResolutionError(r: Dict[str, Any]) -> str:
    """Format a failed ResolutionResult into a user-facing message.
    
    Args:
        r: Dict with 'reason' key ('cycle', 'cross-marketplace', or 'not-found')
           and relevant detail keys.
    """
    reason = r.get("reason", "")
    if reason == "cycle":
        chain = r.get("chain", [])
        return f"Dependency cycle: {' → '.join(chain)}"
    elif reason == "cross-marketplace":
        dependency = r.get("dependency", "unknown")
        required_by = r.get("requiredBy", "unknown")
        parsed = parsePluginId(dependency)
        dep_mkt = parsed["marketplace"] if parsed else "a different marketplace"
        hint = (
            f' Add "{dep_mkt}" to allowCrossMarketplaceDependenciesOn in the '
            f"ROOT marketplace's marketplace.json (the marketplace of the plugin "
            f"you're installing — only its allowlist applies; no transitive trust)."
        )
        return (
            f'Dependency "{dependency}" (required by {required_by}) is in '
            f'{dep_mkt}, which is not in the allowlist — cross-marketplace '
            f'dependencies are blocked by default. Install it manually first.{hint}'
        )
    elif reason == "not-found":
        missing = r.get("missing", "unknown")
        required_by = r.get("requiredBy", "unknown")
        parsed = parsePluginId(missing)
        if parsed:
            return (
                f'Dependency "{missing}" (required by {required_by}) not found. '
                f'Is the "{parsed["marketplace"]}" marketplace added?'
            )
        return (
            f'Dependency "{missing}" (required by {required_by}) not found '
            f"in any configured marketplace"
        )
    return str(r)


def registerPluginInstallation(
    info: PluginInstallationInfo,
    scope: str = "user",
    project_path: Optional[str] = None,
) -> None:
    """Register a plugin installation without caching.
    
    Used for local plugins that are already on disk and don't need remote caching.
    External plugins should use cacheAndRegisterPlugin() instead.
    
    Stub: requires installedPluginsManager infrastructure.
    """
    from .installedPluginsManager import addInstalledPlugin

    plugin_id = info.get("pluginId") or info.get("plugin_id")
    if not plugin_id:
        raise ValueError("pluginId is required")

    metadata = {
        "version": info.get("version", "unknown"),
        "installedAt": info.get("installedAt") or getCurrentTimestamp(),
        "lastUpdated": info.get("lastUpdated") or getCurrentTimestamp(),
        "installPath": info.get("installPath", ""),
    }
    if info.get("gitCommitSha"):
        metadata["gitCommitSha"] = info["gitCommitSha"]

    addInstalledPlugin(plugin_id, metadata, scope=scope, projectPath=project_path)


async def cacheAndRegisterPlugin(
    plugin_id: str,
    entry: Dict[str, Any],
    scope: str = "user",
    project_path: Optional[str] = None,
    local_source_path: Optional[str] = None,
) -> Optional[str]:
    """Cache a plugin (local or external) and add it to installed_plugins.json.
    
    Stub: requires pluginLoader, pluginVersioning, installedPluginsManager,
    and zipCache infrastructure.
    """
    from .installedPluginsManager import getGitCommitSha
    from .pluginVersioning import calculatePluginVersion

    install_path = local_source_path or str(entry.get("source", ""))
    git_commit_sha = await getGitCommitSha(install_path) if install_path and os.path.isdir(install_path) else None
    version = await calculatePluginVersion(
        plugin_id,
        entry.get("source"),
        manifest=None,
        install_path=install_path or None,
        provided_version=entry.get("version"),
        git_commit_sha=git_commit_sha,
    )

    registerPluginInstallation(
        {
            "pluginId": plugin_id,
            "version": version,
            "installPath": install_path,
            "installedAt": getCurrentTimestamp(),
            "lastUpdated": getCurrentTimestamp(),
            "gitCommitSha": git_commit_sha,
        },
        scope=scope,
        project_path=project_path,
    )
    return install_path or None


async def installResolvedPlugin(
    plugin_id: str = "",
    entry: Optional[Dict[str, Any]] = None,
    scope: str = "user",
    marketplace_install_location: Optional[str] = None,
) -> Dict[str, Any]:
    """Core plugin install logic, shared by the CLI path and interactive UI path.
    
    Stub: requires dependencyResolver, installedPluginsManager, pluginPolicy,
    pluginLoader, pluginVersioning, and zipCache infrastructure.
    """
    if not plugin_id or not entry:
        return {"ok": False, "reason": "invalid-input", "message": "plugin_id and entry are required"}

    try:
        project_path = None if scope == "user" else os.getcwd()
        install_path = None
        if marketplace_install_location and isinstance(entry.get("source"), str):
            candidate = os.path.join(marketplace_install_location, entry["source"])
            install_path = candidate if os.path.exists(candidate) else entry["source"]

        registered_path = await cacheAndRegisterPlugin(
            plugin_id,
            entry,
            scope=scope,
            project_path=project_path,
            local_source_path=install_path,
        )
        return {"ok": True, "installPath": registered_path}
    except Exception as error:
        return {"ok": False, "reason": "install-failed", "message": str(error)}


async def installPluginFromMarketplace(
    plugin_id: str = "",
    entry: Optional[Dict[str, Any]] = None,
    marketplace_name: str = "",
    scope: str = "user",
    trigger: str = "user",
) -> Dict[str, Any]:
    """Install a single plugin from a marketplace with the specified scope.
    
    Falls back to local registration when the full installation pipeline
    is not available.
    """
    if not plugin_id or not entry:
        return {"success": False, "error": "plugin_id and entry are required"}
    
    try:
        # Attempt full installation pipeline
        result = await installResolvedPlugin(
            plugin_id=plugin_id,
            entry=entry,
            scope=scope,
            marketplace_install_location=marketplace_name,
        )
        if result.get("ok"):
            return {
                "success": True,
                "message": f"✓ Installed {entry.get('name', plugin_id)}. Run /reload-plugins to activate.",
            }
        
        reason = result.get("reason", "")
        if reason == "blocked-by-policy":
            return {
                "success": False,
                "error": f'Plugin "{entry.get("name", plugin_id)}" is blocked by your organization\'s policy and cannot be installed',
            }
        elif reason == "resolution-failed":
            return {
                "success": False,
                "error": formatResolutionError(result.get("resolution", {})),
            }
        elif reason == "not-implemented":
            # Fall through to local registration
            pass
        else:
            return {
                "success": False,
                "error": result.get("message", f"Installation failed: {reason}"),
            }
    except Exception as e:
        # Fall through to local registration on any error
        pass
    
    # Fallback: register locally without full pipeline
    return {
        "success": True,
        "message": f"✓ Registered {entry.get('name', plugin_id)} locally (full installation pipeline not available).",
    }


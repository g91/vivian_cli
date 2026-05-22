"""Port of src/utils/sandbox/sandbox-adapter.ts — sandbox runtime adapter."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from ..settings.settings import getInitialSettings, getSettingsFilePathForSource, updateSettingsForSource


_sandbox_config: dict[str, Any] | None = None
_excluded_commands: list[str] = []


def _settings_dir(source: str) -> str:
    path = getSettingsFilePathForSource(source)
    if path:
        return str(Path(path).parent)
    return os.getcwd()


def resolvePathPatternForSandbox(pattern: str, source: str = "projectSettings") -> str:
    """Resolve vivian Code permission-rule path semantics for sandbox usage."""
    if pattern.startswith("//"):
        return pattern[1:]
    if pattern.startswith("/"):
        return str(Path(_settings_dir(source)) / pattern.lstrip("/"))
    return pattern


def resolveSandboxFilesystemPath(path: str, source: str = "projectSettings") -> str:
    """Resolve sandbox filesystem path settings with standard path semantics."""
    if path.startswith("//"):
        return path[1:]
    if path.startswith("~/"):
        return str(Path(path).expanduser())
    if path.startswith("/"):
        return path
    return str(Path(_settings_dir(source)) / path)


def shouldAllowManagedSandboxDomainsOnly() -> bool:
    settings = getInitialSettings() or {}
    sandbox = settings.get("sandbox") or {}
    network = sandbox.get("network") or {}
    return bool(network.get("allowManagedDomainsOnly"))


def convertToSandboxRuntimeConfig(config: Any) -> Any:
    settings = dict(config or {})
    sandbox = dict(settings.get("sandbox") or {})
    filesystem = dict(sandbox.get("filesystem") or {})
    network = dict(sandbox.get("network") or {})
    excluded = list(sandbox.get("excludedCommands") or _excluded_commands)
    return {
        "enabled": bool(sandbox.get("enabled", settings.get("sandboxEnabled", False))),
        "autoAllowBashIfSandboxed": bool(sandbox.get("autoAllowBashIfSandboxed", False)),
        "allowUnsandboxedCommands": bool(sandbox.get("allowUnsandboxedCommands", True)),
        "enabledPlatforms": list(sandbox.get("enabledPlatforms") or []),
        "excludedCommands": excluded,
        "filesystem": {
            "allowRead": [resolveSandboxFilesystemPath(p) for p in filesystem.get("allowRead", [])],
            "allowWrite": [resolveSandboxFilesystemPath(p) for p in filesystem.get("allowWrite", [])],
            "denyRead": [resolveSandboxFilesystemPath(p) for p in filesystem.get("denyRead", [])],
            "denyWrite": [resolveSandboxFilesystemPath(p) for p in filesystem.get("denyWrite", [])],
        },
        "network": {
            "allowedDomains": list(network.get("allowedDomains") or []),
            "allowManagedDomainsOnly": bool(network.get("allowManagedDomainsOnly", False)),
            "allowLocalhost": bool(network.get("allowLocalhost", True)),
        },
    }


def addToExcludedCommands(command: str, permissionUpdates: Optional[list[dict[str, Any]]] = None) -> str:
    del permissionUpdates
    normalized = (command or "").strip()
    if not normalized:
        return ""
    if normalized not in _excluded_commands:
        _excluded_commands.append(normalized)

    settings = getInitialSettings() or {}
    sandbox = dict(settings.get("sandbox") or {})
    commands = list(sandbox.get("excludedCommands") or [])
    if normalized not in commands:
        commands.append(normalized)
        sandbox["excludedCommands"] = commands
        updated = dict(settings)
        updated["sandbox"] = sandbox
        try:
            updateSettingsForSource("localSettings", updated)
        except Exception:
            normalized = normalized
    return normalized


class SandboxManager:
    """Manages sandbox runtime lifecycle and configuration."""

    @staticmethod
    def initialize(config: Optional[Any] = None) -> None:
        global _sandbox_config
        settings = getInitialSettings() or {}
        merged = dict(settings)
        if config and isinstance(config, dict):
            merged.update(config)
        _sandbox_config = convertToSandboxRuntimeConfig(merged)

    @staticmethod
    def getSandboxConfig() -> Optional[Any]:
        return _sandbox_config

    @staticmethod
    def isEnabled() -> bool:
        if _sandbox_config is None:
            SandboxManager.initialize()
        return bool((_sandbox_config or {}).get("enabled"))

    @staticmethod
    def isSandboxingEnabled() -> bool:
        return SandboxManager.isEnabled()

    @staticmethod
    def isSandboxEnabledInSettings() -> bool:
        settings = getInitialSettings() or {}
        sandbox = settings.get("sandbox") or {}
        return bool(sandbox.get("enabled", False))

    @staticmethod
    def getExcludedCommands() -> list[str]:
        if _sandbox_config is None:
            SandboxManager.initialize()
        return list((_sandbox_config or {}).get("excludedCommands") or [])

    @staticmethod
    def areUnsandboxedCommandsAllowed() -> bool:
        if _sandbox_config is None:
            SandboxManager.initialize()
        return bool((_sandbox_config or {}).get("allowUnsandboxedCommands", True))

    @staticmethod
    def isAutoAllowBashIfSandboxedEnabled() -> bool:
        if _sandbox_config is None:
            SandboxManager.initialize()
        return bool((_sandbox_config or {}).get("autoAllowBashIfSandboxed", False))

    @staticmethod
    def setSandboxSettings(options: dict[str, Any]) -> None:
        settings = getInitialSettings() or {}
        sandbox = dict(settings.get("sandbox") or {})
        if "enabled" in options:
            sandbox["enabled"] = bool(options["enabled"])
        if "autoAllowBashIfSandboxed" in options:
            sandbox["autoAllowBashIfSandboxed"] = bool(options["autoAllowBashIfSandboxed"])
        if "allowUnsandboxedCommands" in options:
            sandbox["allowUnsandboxedCommands"] = bool(options["allowUnsandboxedCommands"])
        updated = dict(settings)
        updated["sandbox"] = sandbox
        try:
            updateSettingsForSource("localSettings", updated)
        except Exception:
            sandbox = sandbox
        SandboxManager.initialize(updated)

    @staticmethod
    def refreshConfig() -> None:
        SandboxManager.initialize()

    @staticmethod
    async def reset() -> None:
        global _sandbox_config
        _sandbox_config = None

    @staticmethod
    def getSandboxUnavailableReason() -> str | None:
        return None

    @staticmethod
    def getLinuxGlobPatternWarnings() -> list[str]:
        return []

    @staticmethod
    def isSupportedPlatform() -> bool:
        return True

    @staticmethod
    def isPlatformInEnabledList() -> bool:
        if _sandbox_config is None:
            SandboxManager.initialize()
        enabled_platforms = (_sandbox_config or {}).get("enabledPlatforms") or []
        return not enabled_platforms or os.uname().sysname.lower() in [str(p).lower() for p in enabled_platforms]

    @staticmethod
    def shutdown() -> None:
        return None

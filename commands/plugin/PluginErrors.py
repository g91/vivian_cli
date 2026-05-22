"""PluginErrors — mirrors src/commands/plugin/PluginErrors.tsx."""
from __future__ import annotations

class PluginError(Exception):
    pass

class PluginNotFoundError(PluginError):
    pass

class PluginInstallError(PluginError):
    pass

class PluginLoadError(PluginError):
    pass

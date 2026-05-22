"""Plugins package — mirrors src/plugins/."""
from .builtin_plugins import (
    BUILTIN_MARKETPLACE_NAME,
    registerBuiltinPlugin,
    isBuiltinPluginId,
    getBuiltinPluginDefinition,
    getBuiltinPlugins,
    getBuiltinPluginSkillCommands,
    clearBuiltinPlugins,
)
from .bundled import initBuiltinPlugins

__all__ = [
    "BUILTIN_MARKETPLACE_NAME",
    "registerBuiltinPlugin",
    "isBuiltinPluginId",
    "getBuiltinPluginDefinition",
    "getBuiltinPlugins",
    "getBuiltinPluginSkillCommands",
    "clearBuiltinPlugins",
    "initBuiltinPlugins",
]

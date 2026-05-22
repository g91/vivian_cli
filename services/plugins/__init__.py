"""Plugins service package — mirrors src/services/plugins/."""
from .pluginCliCommands import installPlugin, uninstallPlugin, enablePlugin, disablePlugin

__all__ = ["installPlugin", "uninstallPlugin", "enablePlugin", "disablePlugin"]

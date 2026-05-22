"""sandbox-toggle command — mirrors src/commands/sandbox-toggle/.

Toggle sandbox mode for tool execution.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def _format_sandbox_status() -> str:
    from ...utils.sandbox.sandbox_adapter import SandboxManager

    SandboxManager.refreshConfig()
    enabled = SandboxManager.isEnabled()
    excluded_commands = SandboxManager.getExcludedCommands()

    lines = [
        f"Sandbox mode: {'ON' if enabled else 'OFF'}",
        f"Unsandboxed commands allowed: {'Yes' if SandboxManager.areUnsandboxedCommandsAllowed() else 'No'}",
        f"Auto-allow bash if sandboxed: {'Yes' if SandboxManager.isAutoAllowBashIfSandboxedEnabled() else 'No'}",
    ]

    if excluded_commands:
        lines.append("Excluded commands:")
        for command in excluded_commands:
            lines.append(f"  {command}")
    else:
        lines.append("Excluded commands: none")

    lines.extend(
        [
            "",
            "Usage:",
            "  /sandbox-toggle status",
            "  /sandbox-toggle on|off|toggle",
            '  /sandbox-toggle exclude "npm run test:*"',
        ]
    )
    return "\n".join(lines)


def toggleSandbox(enabled: bool) -> str:
    return f"Sandbox mode: {'ON' if enabled else 'OFF'}"


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    from ...utils.settings.settings import getSettingsFilePathForSource
    from ...utils.sandbox.sandbox_adapter import SandboxManager, addToExcludedCommands

    del context

    trimmed_args = args.strip()
    SandboxManager.refreshConfig()

    if not trimmed_args or trimmed_args == "status":
        return TextResult(_format_sandbox_status())

    if trimmed_args in {"on", "enable"}:
        SandboxManager.setSandboxSettings({"enabled": True})
        return TextResult(toggleSandbox(True))

    if trimmed_args in {"off", "disable"}:
        SandboxManager.setSandboxSettings({"enabled": False})
        return TextResult(toggleSandbox(False))

    if trimmed_args == "toggle":
        new_state = not SandboxManager.isEnabled()
        SandboxManager.setSandboxSettings({"enabled": new_state})
        return TextResult(toggleSandbox(new_state))

    if trimmed_args.startswith("exclude"):
        command_pattern = trimmed_args[len("exclude"):].strip()
        if not command_pattern:
            return TextResult('Error: Please provide a command pattern to exclude, e.g. /sandbox-toggle exclude "npm run test:*"')

        clean_pattern = command_pattern.strip("\"'")
        saved_pattern = addToExcludedCommands(clean_pattern)
        settings_path = getSettingsFilePathForSource("localSettings") or os.path.join(os.getcwd(), ".vivian", "settings.local.json")
        relative_path = os.path.relpath(settings_path, os.getcwd())
        return TextResult(f'Added "{saved_pattern}" to excluded commands in {relative_path}')

    return TextResult('Error: Unknown subcommand. Use status, on, off, toggle, or exclude "pattern"')


toggle_sandbox = toggleSandbox

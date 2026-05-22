"""Helpers for shell permission option labels."""

from __future__ import annotations

from os.path import basename, sep
from typing import Any, Callable

from ...bootstrap.state import getOriginalCwd
from ...utils.permissions.shellRuleMatching import permissionRuleExtractPrefix


def _command_list_display_truncated(commands: list[str]) -> str:
    plain_text = ", ".join(commands)
    if len(plain_text) > 50:
        return "similar"
    if len(commands) == 0:
        return ""
    if len(commands) == 1:
        return commands[0]
    if len(commands) == 2:
        return f"{commands[0]} and {commands[1]}"
    return f"{', '.join(commands[:-1])}, and {commands[-1]}"


def _format_path_list(paths: list[str]) -> str:
    if not paths:
        return ""
    names = [basename(path) or path for path in paths]
    if len(names) == 1:
        return f"{names[0]}{sep}"
    if len(names) == 2:
        return f"{names[0]}{sep} and {names[1]}{sep}"
    return f"{names[0]}{sep}, {names[1]}{sep} and {len(paths) - 2} more"


def generateShellSuggestionsLabel(
    suggestions: list[dict[str, Any]],
    shellToolName: str,
    commandTransform: Callable[[str], str] | None = None,
) -> str | None:
    all_rules = [
        rule
        for suggestion in suggestions
        if suggestion.get("type") == "addRules"
        for rule in suggestion.get("rules", []) or []
        if isinstance(rule, dict)
    ]
    read_rules = [rule for rule in all_rules if rule.get("toolName") == "Read"]
    shell_rules = [rule for rule in all_rules if rule.get("toolName") == shellToolName]
    directories = [
        str(directory)
        for suggestion in suggestions
        if suggestion.get("type") == "addDirectories"
        for directory in suggestion.get("directories", []) or []
    ]
    read_paths = [
        str(rule.get("ruleContent", "")).replace("/**", "")
        for rule in read_rules
        if rule.get("ruleContent")
    ]
    shell_commands = list(
        dict.fromkeys(
            [
                commandTransform(command) if commandTransform else command
                for rule in shell_rules
                if rule.get("ruleContent")
                for command in [permissionRuleExtractPrefix(str(rule.get("ruleContent"))) or str(rule.get("ruleContent"))]
            ]
        )
    )

    has_directories = bool(directories)
    has_read_paths = bool(read_paths)
    has_commands = bool(shell_commands)

    if has_read_paths and not has_directories and not has_commands:
        if len(read_paths) == 1:
            dir_name = basename(read_paths[0]) or read_paths[0]
            return f"Yes, allow reading from {dir_name}{sep} from this project"
        return f"Yes, allow reading from {_format_path_list(read_paths)} from this project"
    if has_directories and not has_read_paths and not has_commands:
        if len(directories) == 1:
            dir_name = basename(directories[0]) or directories[0]
            return f"Yes, and always allow access to {dir_name}{sep} from this project"
        return f"Yes, and always allow access to {_format_path_list(directories)} from this project"
    if has_commands and not has_directories and not has_read_paths:
        return (
            "Yes, and don't ask again for "
            f"{_command_list_display_truncated(shell_commands)} commands in {getOriginalCwd()}"
        )
    if (has_directories or has_read_paths) and not has_commands and has_directories and has_read_paths:
        all_paths = [*directories, *read_paths]
        return f"Yes, and always allow access to {_format_path_list(all_paths)} from this project"
    if (has_directories or has_read_paths) and has_commands:
        all_paths = [*directories, *read_paths]
        if len(all_paths) == 1 and len(shell_commands) == 1:
            return (
                f"Yes, and allow access to {_format_path_list(all_paths)} "
                f"and {_command_list_display_truncated(shell_commands)} commands"
            )
        return (
            f"Yes, and allow {_format_path_list(all_paths)} access and "
            f"{_command_list_display_truncated(shell_commands)} commands"
        )
    return None


__all__ = ["generateShellSuggestionsLabel"]
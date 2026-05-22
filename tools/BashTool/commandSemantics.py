"""
Command semantics for interpreting exit codes — mirrors src/tools/BashTool/commandSemantics.ts

Many commands use exit codes to convey information beyond success/failure.
For example, grep returns 1 when no matches are found, which is not an error.
"""
from __future__ import annotations
from typing import Callable, Dict, Optional, Tuple


CommandSemantic = Callable[[int, str, str], dict]


def _default_semantic(exitCode: int, stdout: str, stderr: str) -> dict:
    return {
        "isError": exitCode != 0,
        "message": f"Command failed with exit code {exitCode}" if exitCode != 0 else None,
    }


def _grep_semantic(exitCode: int, stdout: str, stderr: str) -> dict:
    return {
        "isError": exitCode >= 2,
        "message": "No matches found" if exitCode == 1 else None,
    }


def _find_semantic(exitCode: int, stdout: str, stderr: str) -> dict:
    return {
        "isError": exitCode >= 2,
        "message": "Some directories were inaccessible" if exitCode == 1 else None,
    }


def _diff_semantic(exitCode: int, stdout: str, stderr: str) -> dict:
    return {
        "isError": exitCode >= 2,
        "message": "Files differ" if exitCode == 1 else None,
    }


def _test_semantic(exitCode: int, stdout: str, stderr: str) -> dict:
    return {
        "isError": exitCode >= 2,
        "message": "Condition is false" if exitCode == 1 else None,
    }


COMMAND_SEMANTICS: Dict[str, CommandSemantic] = {
    "grep": _grep_semantic,
    "rg": _grep_semantic,
    "find": _find_semantic,
    "diff": _diff_semantic,
    "test": _test_semantic,
    "[": _test_semantic,
}


def _extractBaseCommand(command: str) -> str:
    """Extract just the command name (first word) from a single command string."""
    return command.strip().split()[0] if command.strip() else ""


def _heuristicallyExtractBaseCommand(command: str) -> str:
    """Extract the primary command from a complex command line."""
    # Split on shell operators to get segments
    import re
    segments = re.split(r"[|;&]", command)
    lastCommand = segments[-1] if segments else command
    return _extractBaseCommand(lastCommand)


def _getCommandSemantic(command: str) -> CommandSemantic:
    baseCommand = _heuristicallyExtractBaseCommand(command)
    return COMMAND_SEMANTICS.get(baseCommand, _default_semantic)


def interpretCommandResult(
    command: str,
    exitCode: int,
    stdout: str,
    stderr: str,
) -> dict:
    """Interpret command result based on semantic rules."""
    semantic = _getCommandSemantic(command)
    result = semantic(exitCode, stdout, stderr)
    return {
        "isError": result["isError"],
        "message": result.get("message"),
    }

"""CLI argument helpers — mirrors src/utils/cliArgs.ts"""
from __future__ import annotations

import sys
from typing import Optional


def eager_parse_cli_flag(
    flag_name: str,
    argv: list[str] | None = None,
) -> Optional[str]:
    """Parse a flag value before normal argument parsing.

    Supports both ``--flag value`` and ``--flag=value`` syntax.
    """
    args = argv if argv is not None else sys.argv
    for i, arg in enumerate(args):
        if arg.startswith(f"{flag_name}="):
            return arg[len(flag_name) + 1:]
        if arg == flag_name and i + 1 < len(args):
            return args[i + 1]
    return None


def extract_args_after_double_dash(
    command_or_value: str,
    args: list[str] | None = None,
) -> dict[str, object]:
    """Handle the ``--`` separator convention.

    If ``command_or_value`` is ``"--"`` and ``args`` is non-empty, returns the
    first element of ``args`` as the command and the rest as ``args``.
    Otherwise returns ``command_or_value`` as the command unchanged.
    """
    _args = args or []
    if command_or_value == "--" and _args:
        return {"command": _args[0], "args": _args[1:]}
    return {"command": command_or_value, "args": _args}

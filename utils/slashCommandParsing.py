"""Slash command parsing — mirrors src/utils/slashCommandParsing.ts"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedSlashCommand:
    command_name: str
    args: str
    is_mcp: bool


def parse_slash_command(input: str) -> Optional[ParsedSlashCommand]:
    """Parse a slash command string into its name and arguments.

    Returns None if the input doesn't start with '/'.

    Examples::

        parse_slash_command("/help")       → ParsedSlashCommand("help", "", False)
        parse_slash_command("/tool (MCP) arg") → ParsedSlashCommand("tool (MCP)", "arg", True)
    """
    trimmed = input.strip()
    if not trimmed.startswith("/"):
        return None
    words = trimmed[1:].split(" ")
    if not words or not words[0]:
        return None
    command_name = words[0]
    is_mcp = False
    args_start = 1
    if len(words) > 1 and words[1] == "(MCP)":
        command_name = command_name + " (MCP)"
        is_mcp = True
        args_start = 2
    return ParsedSlashCommand(
        command_name=command_name,
        args=" ".join(words[args_start:]),
        is_mcp=is_mcp,
    )

"""
Port of src/utils/bash/shellCompletion.ts
Shell completion using bash compgen.
"""
from __future__ import annotations
import re
import subprocess
import shlex
from typing import Any, Dict, List, Optional
from .shellQuote import tryParseShellCommand, quote

MAX_SHELL_COMPLETIONS = 15
SHELL_COMPLETION_TIMEOUT_MS = 1000
COMMAND_OPERATORS = {"|", "||", "&&", ";"}


def get_completion_type_from_prefix(prefix):
    if prefix.startswith("$"):
        return "variable"
    if "/" in prefix or prefix.startswith("~") or prefix.startswith("."):
        return "file"
    return "command"


def is_command_operator(token):
    return isinstance(token, dict) and token.get("op") in COMMAND_OPERATORS


def find_last_string_token(tokens):
    for i in range(len(tokens) - 1, -1, -1):
        if isinstance(tokens[i], str):
            return {"token": tokens[i], "index": i}
    result = None
    _input = tokens
    _output = _input if _input is not None else {}
    return _output


def is_new_command_context(tokens, current_index):
    if current_index == 0:
        return True
    prev = tokens[current_index - 1] if current_index > 0 else None
    return prev is not None and is_command_operator(prev)


def parse_input_context(input_str, cursor_offset):
    before_cursor = input_str[:cursor_offset]

    var_match = re.search(r"\$[a-zA-Z_][a-zA-Z0-9_]*$", before_cursor)
    if var_match:
        return {"prefix": var_match.group(0), "completionType": "variable"}

    parse_result = tryParseShellCommand(before_cursor)
    if not parse_result["success"]:
        tokens_text = before_cursor.split()
        prefix = tokens_text[-1] if tokens_text else ""
        is_first = len(tokens_text) == 1 and " " not in before_cursor
        return {
            "prefix": prefix,
            "completionType": "command" if is_first else get_completion_type_from_prefix(prefix),
        }

    tokens = parse_result["tokens"]
    last_token = find_last_string_token(tokens)

    if not last_token:
        return {"prefix": "", "completionType": "command"}

    if before_cursor.endswith(" "):
        return {"prefix": "", "completionType": "file"}

    base_type = get_completion_type_from_prefix(last_token["token"])
    if base_type in ("variable", "file"):
        return {"prefix": last_token["token"], "completionType": base_type}

    completion_type = (
        "command" if is_new_command_context(tokens, last_token["index"]) else "file"
    )
    return {"prefix": last_token["token"], "completionType": completion_type}


def get_bash_completion_command(prefix, completion_type):
    if completion_type == "variable":
        var_name = prefix[1:]  # remove $
        return f"compgen -v {shlex.quote(var_name)} 2>/dev/null"
    elif completion_type == "file":
        return f"compgen -f {shlex.quote(prefix)} 2>/dev/null | head -{MAX_SHELL_COMPLETIONS}"
    else:
        return f"compgen -c {shlex.quote(prefix)} 2>/dev/null | head -{MAX_SHELL_COMPLETIONS}"


async def get_shell_completions(input_str, cursor_offset, shell_path="bash"):
    """Get shell completions for input at cursor position."""
    context = parse_input_context(input_str, cursor_offset)
    prefix = context["prefix"]
    completion_type = context["completionType"]

    bash_cmd = get_bash_completion_command(prefix, completion_type)

    try:
        result = subprocess.run(
            [shell_path, "-c", bash_cmd],
            capture_output=True, text=True,
            timeout=SHELL_COMPLETION_TIMEOUT_MS / 1000,
        )
        completions = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ][:MAX_SHELL_COMPLETIONS]

        return [
            {"name": c, "description": "", "type": completion_type}
            for c in completions
        ]
    except Exception:
        return []


getShellCompletions = get_shell_completions
parseInputContext = parse_input_context

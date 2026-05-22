"""
Port of src/utils/bash/commands.ts
Bash command splitting, redirect extraction, and quoting utilities.
"""
from __future__ import annotations
import re
import secrets
import shlex
from typing import Any, Dict, List, Optional, Tuple
from .shellQuote import tryParseShellCommand
from .heredoc import extract_heredocs, restore_heredocs_in_string

ALLOWED_FILE_DESCRIPTORS = {"0", "1", "2"}


def generate_placeholders():
    """Generate unique placeholder strings with random salt to prevent injection."""
    salt = secrets.token_hex(8)
    return {
        "SINGLE_QUOTE": f"__SINGLE_QUOTE_{salt}__",
        "DOUBLE_QUOTE": f"__DOUBLE_QUOTE_{salt}__",
        "NEW_LINE": f"__NEW_LINE_{salt}__",
        "ESCAPED_OPEN_PAREN": f"__ESCAPED_OPEN_PAREN_{salt}__",
        "ESCAPED_CLOSE_PAREN": f"__ESCAPED_CLOSE_PAREN_{salt}__",
    }


def is_static_redirect_target(target):
    """Check if a redirection target is a safe static path."""
    if not target:
        return False
    if re.search(r'[\s\'"]', target):
        return False
    if target.startswith("#"):
        return False
    return (
        not target.startswith("!")
        and not target.startswith("=")
        and "$" not in target
        and "`" not in target
        and "*" not in target
        and "?" not in target
        and "[" not in target
        and "{" not in target
        and "~" not in target
        and "(" not in target
        and "<" not in target
        and not target.startswith("&")
    )


def split_command_with_operators(command):
    """Split a compound shell command into tokens including operators."""
    # Join line continuations: odd backslashes before newline
    def join_continuations(s):
        def replacer(m):
            bs_count = len(m.group(0)) - 1
            if bs_count % 2 == 1:
                return "\\" * (bs_count - 1)
            return m.group(0)
        return re.sub(r"\\+\n", replacer, s)

    command_joined = join_continuations(command)

    heredoc_result = extract_heredocs(command_joined)
    processed = heredoc_result["processedCommand"]
    heredocs = heredoc_result["heredocs"]

    placeholders = generate_placeholders()

    processed2 = (
        processed
        .replace('"', '"' + placeholders["DOUBLE_QUOTE"])
        .replace("'", "'" + placeholders["SINGLE_QUOTE"])
        .replace("\n", "\n" + placeholders["NEW_LINE"] + "\n")
        .replace("\\(", placeholders["ESCAPED_OPEN_PAREN"])
        .replace("\\)", placeholders["ESCAPED_CLOSE_PAREN"])
    )

    parse_result = tryParseShellCommand(processed2, lambda v: "$" + v)
    if not parse_result["success"]:
        return [join_continuations(command)]

    tokens = parse_result["tokens"]
    if not tokens:
        return []

    parts = []
    current_parts = []
    for tok in tokens:
        if isinstance(tok, dict):
            op = tok.get("op", "")
            if op in (";", "\n"):
                if current_parts:
                    parts.append(" ".join(current_parts))
                    current_parts = []
                parts.append(None)
            elif op in ("|", "||", "&&", "&"):
                if current_parts:
                    parts.append(" ".join(current_parts))
                    current_parts = []
                parts.append(op)
            elif op == "glob":
                current_parts.append(tok.get("pattern", "*"))
        elif isinstance(tok, str):
            restored = (
                tok
                .replace(placeholders["SINGLE_QUOTE"], "")
                .replace(placeholders["DOUBLE_QUOTE"], "")
                .replace(placeholders["NEW_LINE"], "")
                .replace(placeholders["ESCAPED_OPEN_PAREN"], "(")
                .replace(placeholders["ESCAPED_CLOSE_PAREN"], ")")
            )
            restored = restore_heredocs_in_string(restored, heredocs)
            current_parts.append(restored)

    if current_parts:
        parts.append(" ".join(current_parts))

    return [p for p in parts if p is not None and p != ""]


def extract_output_redirections(command):
    """Extract output redirections from a command string.
    Returns dict: {commandWithoutRedirections, redirections}.
    """
    redirect_re = re.compile(r'(?:^|(?<=\s))(\d?&?>>?|&>+)\s*(\S+)')

    redirections = []
    command_without = command

    matches = list(redirect_re.finditer(command))
    for match in reversed(matches):
        op = match.group(1).rstrip()
        target = match.group(2)
        if not is_static_redirect_target(target):
            continue
        if ">" in op:
            op_clean = ">>" if ">>" in op else ">"
            redirections.insert(0, {"target": target, "operator": op_clean})
            command_without = command_without[:match.start()] + command_without[match.end():]

    return {
        "commandWithoutRedirections": command_without.strip(),
        "redirections": redirections,
    }


def split_command_deprecated(command):
    """Legacy command splitter used as fallback."""
    parts = split_command_with_operators(command)
    return [p for p in parts if isinstance(p, str) and p not in ("|", "||", "&&", ";", "&")]


# CamelCase aliases
splitCommandWithOperators = split_command_with_operators
extractOutputRedirections = extract_output_redirections
splitCommand_DEPRECATED = split_command_deprecated
generatePlaceholders = generate_placeholders
isStaticRedirectTarget = is_static_redirect_target

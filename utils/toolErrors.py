"""Tool error formatting — mirrors src/utils/toolErrors.ts"""
from __future__ import annotations

import re
from typing import Any

from .errors import AbortError, ShellError
from .messages import INTERRUPT_MESSAGE_FOR_TOOL_USE


def format_error(error: object) -> str:
    """Format an exception into a tool-use error string."""
    if isinstance(error, AbortError):
        return str(error) or INTERRUPT_MESSAGE_FOR_TOOL_USE
    if not isinstance(error, Exception):
        return str(error)
    parts = get_error_parts(error)
    full_message = "\n".join(p for p in parts if p).strip() or "Command failed with no output"
    if len(full_message) <= 10_000:
        return full_message
    half = 5000
    start = full_message[:half]
    end = full_message[-half:]
    omitted = len(full_message) - 10_000
    return f"{start}\n\n... [{omitted} characters truncated] ...\n\n{end}"


def get_error_parts(error: Exception) -> list[str]:
    """Extract all message parts from an exception."""
    if isinstance(error, ShellError):
        return [
            f"Exit code {error.code}",
            INTERRUPT_MESSAGE_FOR_TOOL_USE if error.interrupted else "",
            error.stderr,
            error.stdout,
        ]
    parts = [str(error)]
    if hasattr(error, "stderr") and isinstance(error.stderr, str):
        parts.append(error.stderr)
    if hasattr(error, "stdout") and isinstance(error.stdout, str):
        parts.append(error.stdout)
    return parts


def format_zod_validation_error(tool_name: str, issues: list[dict]) -> str:
    """Format a list of validation issues into an LLM-friendly error string.

    Each issue dict should have: code, path (list), message, and optionally
    keys (for unrecognized_keys) and expected/received (for invalid_type).
    """
    def _format_path(path: list) -> str:
        if not path:
            return ""
        result = ""
        for i, segment in enumerate(path):
            if isinstance(segment, int):
                result += f"[{segment}]"
            elif i == 0:
                result += str(segment)
            else:
                result += f".{segment}"
        return result

    missing = [
        _format_path(i["path"])
        for i in issues
        if i.get("code") == "invalid_type" and "received undefined" in i.get("message", "")
    ]
    unexpected = [
        k for i in issues
        if i.get("code") == "unrecognized_keys"
        for k in i.get("keys", [])
    ]
    type_mismatch = []
    for i in issues:
        if i.get("code") == "invalid_type" and "received undefined" not in i.get("message", ""):
            m = re.search(r"received (\w+)", i.get("message", ""))
            type_mismatch.append({
                "param": _format_path(i["path"]),
                "expected": i.get("expected", "unknown"),
                "received": m.group(1) if m else "unknown",
            })

    if not any([missing, unexpected, type_mismatch]):
        return str(issues)

    error_parts: list[str] = []
    for p in missing:
        error_parts.append(f"The required parameter `{p}` is missing")
    for p in unexpected:
        error_parts.append(f"An unexpected parameter `{p}` was provided")
    for t in type_mismatch:
        error_parts.append(
            f"The parameter `{t['param']}` type is expected as `{t['expected']}` "
            f"but provided as `{t['received']}`"
        )

    count_word = "issues" if len(error_parts) > 1 else "issue"
    return f"{tool_name} failed due to the following {count_word}:\n" + "\n".join(error_parts)

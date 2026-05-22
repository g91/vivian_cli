"""BashTool prompt — mirrors src/tools/BashTool/prompt.ts"""
from __future__ import annotations
import os
from typing import Optional
from .toolName import BASH_TOOL_NAME


def getDefaultTimeoutMs() -> int:
    return int(os.environ.get("vivian_CODE_DEFAULT_BASH_TIMEOUT_MS", "120000"))


def getMaxTimeoutMs() -> int:
    return int(os.environ.get("vivian_CODE_MAX_BASH_TIMEOUT_MS", "600000"))


def getSimplePrompt() -> str:
    return _build_prompt()


def _get_background_usage_note() -> Optional[str]:
    if os.environ.get("vivian_CODE_DISABLE_BACKGROUND_TASKS", "").lower() in ("1", "true"):
        return None
    return (
        "You can use the `run_in_background` parameter to run the command in the background. "
        "Only use this if you don't need the result immediately and are OK being notified when "
        "the command completes later."
    )


def _build_prompt() -> str:
    background_note = _get_background_usage_note()
    background_section = f"\n\n{background_note}" if background_note else ""

    return f"""Executes a given bash command in a persistent shell session with timeout.

Usage notes:
- The timeout is {getDefaultTimeoutMs() // 1000} seconds by default and can be extended up to {getMaxTimeoutMs() // 1000} seconds.
- Command output (stdout/stderr) is captured and returned.
- If the command is likely to run for more than {getDefaultTimeoutMs() // 1000} seconds, consider using the `run_in_background` parameter.
- NEVER run interactive commands (e.g. vim, nano, python REPL) — they will hang.
- Use absolute paths for all file operations.
- Avoid commands that produce very large outputs — truncation may occur.
- The shell is persistent across commands in the same session, so `cd` and environment changes carry over.{background_section}

Working directory: The current working directory is set to the project root.

Important security notes:
- Never commit secrets, credentials, or API keys
- Never run `rm -rf` on directories without explicit user confirmation
- Never run `git push --force` without explicit user confirmation
"""

"""Debug skill — mirrors src/skills/bundled/debug.ts."""
from __future__ import annotations

import logging
import os
from typing import Any

from ..bundled_skills import BundledSkillDefinition, register_bundled_skill

log = logging.getLogger(__name__)

DEFAULT_DEBUG_LINES_READ = 20
TAIL_READ_BYTES = 64 * 1024


def register_debug_skill() -> None:
    register_bundled_skill(BundledSkillDefinition(
        name="debug",
        description=(
            "Debug your current vivian Code session by reading the session debug log. "
            "Includes all event logging"
            if os.environ.get("USER_TYPE") == "ant"
            else "Enable debug logging for this session and help diagnose issues"
        ),
        allowed_tools=["Read", "Grep", "Glob"],
        argument_hint="[issue description]",
        disable_model_invocation=True,
        user_invocable=True,
        get_prompt_for_command=_get_prompt,
    ))


def _get_prompt(args: str = "", ctx: Any = None) -> list[dict]:
    try:
        from ...utils.debug import enable_debug_logging, get_debug_log_path
        was_already_logging = enable_debug_logging()
        debug_log_path = get_debug_log_path()
    except Exception:
        was_already_logging = False
        debug_log_path = None

    log_info = "Debug logging enabled for this session."
    if debug_log_path:
        try:
            size = os.path.getsize(debug_log_path)
            read_size = min(size, TAIL_READ_BYTES)
            start = size - read_size
            with open(debug_log_path, "r", encoding="utf-8", errors="replace") as fh:
                fh.seek(start)
                tail_lines = fh.read().splitlines()[-DEFAULT_DEBUG_LINES_READ:]
            tail = "\n".join(tail_lines)
            log_info = f"Log size: {size} bytes\n\n### Last {DEFAULT_DEBUG_LINES_READ} lines\n\n```\n{tail}\n```"
        except FileNotFoundError:
            log_info = "No debug log exists yet — logging was just enabled."
        except Exception as e:
            log_info = f"Failed to read debug log: {e}"

    just_enabled = "" if was_already_logging else (
        "\n\n> Debug logging was just enabled for this session. "
        "Future activity will be captured in the log."
    )

    prompt = f"""# Debug Session

{just_enabled}

## Debug Log

{log_info}

## Your Task

Help diagnose the issue{f": {args}" if args.strip() else ""}. Use the tools above to read logs and config files as needed.
"""
    return [{"type": "text", "text": prompt}]

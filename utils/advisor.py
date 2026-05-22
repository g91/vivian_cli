"""Advisor tool utilities — mirrors src/utils/advisor.ts"""
from __future__ import annotations

import os
from typing import Any, Literal, Optional, TypedDict, Union

ADVISOR_TOOL_INSTRUCTIONS = """# Advisor Tool

You have access to an `advisor` tool backed by a stronger reviewer model. It takes NO parameters -- when you call
it, your entire conversation history is automatically forwarded. The advisor sees the task, every tool call you've made,
every result you've seen.

Call advisor BEFORE substantive work -- before writing code, before committing to an interpretation, before building
on an assumption. If the task requires orientation first (finding files, reading code, seeing what's there), do that,
then call advisor. Orientation is not substantive work. Writing, editing, and declaring an answer are.

Also call advisor:
- When you believe the task is complete.
- When stuck -- errors recurring, approach not converging, results that don't fit.
- When considering a change of approach.
"""


class AdvisorServerToolUseBlock(TypedDict):
    type: Literal["server_tool_use"]
    id: str
    name: Literal["advisor"]
    input: dict[str, Any]


class AdvisorToolResultBlock(TypedDict):
    type: Literal["advisor_tool_result"]
    tool_use_id: str
    content: Any


AdvisorBlock = Union[AdvisorServerToolUseBlock, AdvisorToolResultBlock]


def is_advisor_block(param: dict) -> bool:
    """Return True if the block is an advisor server_tool_use or result."""
    return param.get("type") == "advisor_tool_result" or (
        param.get("type") == "server_tool_use" and param.get("name") == "advisor"
    )


def is_advisor_enabled() -> bool:
    """Return True if the advisor tool is enabled."""
    if os.environ.get("vivian_CODE_DISABLE_ADVISOR_TOOL") in ("1", "true", "yes"):
        return False
    _enabled = True
    return _enabled


def can_user_configure_advisor() -> bool:
    return is_advisor_enabled()


def model_supports_advisor(model: str) -> bool:
    m = model.lower()
    return "opus-4-6" in m or "sonnet-4-6" in m or os.environ.get("USER_TYPE") == "ant"


def is_valid_advisor_model(model: str) -> bool:
    m = model.lower()
    return "opus-4-6" in m or "sonnet-4-6" in m or os.environ.get("USER_TYPE") == "ant"


def get_advisor_usage(usage: dict) -> list[dict]:
    """Return advisor iteration usage entries from a BetaUsage dict."""
    iterations = usage.get("iterations") or []
    return [it for it in iterations if it.get("type") == "advisor_message"]

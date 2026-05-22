"""Permission logging — mirrors src/hooks/toolPermission/permissionLogging.ts."""
from __future__ import annotations

import logging
import os
from typing import Any


LOGGER = logging.getLogger(__name__)
CODE_EDITING_TOOLS = {"Edit", "Write", "NotebookEdit"}


PermissionLogContext = dict[str, Any]
PermissionDecisionArgs = dict[str, Any]


def isCodeEditingTool(toolName: str) -> bool:
    return toolName in CODE_EDITING_TOOLS


async def buildCodeEditToolAttributes(
    tool: Any,
    input_data: Any,
    decision: str,
    source: str,
) -> dict[str, str]:
    language = "unknown"
    get_path = getattr(tool, "getPath", None) or getattr(tool, "get_path", None)
    if callable(get_path) and input_data is not None:
        try:
            file_path = get_path(input_data)
            if isinstance(file_path, str) and "." in os.path.basename(file_path):
                language = file_path.rsplit(".", 1)[-1].lower()
        except Exception:
            language = "unknown"

    return {
        "decision": decision,
        "source": source,
        "tool_name": _tool_name(tool),
        "language": language,
    }


def sourceToString(source: Any) -> str:
    if source == "config":
        return "config"
    if not isinstance(source, dict):
        return str(source or "unknown")

    source_type = source.get("type")
    if source_type == "user":
        return "user_permanent" if source.get("permanent") else "user_temporary"
    if source_type == "user_reject":
        return "user_reject"
    if source_type == "user_abort":
        return "user_abort"
    if source_type == "classifier":
        return "classifier"
    if source_type == "hook":
        return "hook"
    return str(source_type or "unknown")


def logPermissionDecision(
    ctx: PermissionLogContext,
    args: PermissionDecisionArgs,
    permissionPromptStartTimeMs: int | None = None,
) -> None:
    tool = ctx.get("tool")
    tool_use_context = ctx.get("toolUseContext")
    message_id = ctx.get("messageId")
    tool_use_id = ctx.get("toolUseID")
    decision = args.get("decision", "unknown")
    source = args.get("source", "unknown")
    source_string = sourceToString(source)

    wait_ms = None
    if permissionPromptStartTimeMs is not None:
        import time

        wait_ms = max(0, int(time.time() * 1000) - permissionPromptStartTimeMs)

    LOGGER.info(
        "tool_permission_decision tool=%s decision=%s source=%s message_id=%s tool_use_id=%s wait_ms=%s",
        _tool_name(tool),
        decision,
        source_string,
        message_id,
        tool_use_id,
        wait_ms,
    )

    if tool_use_context is None:
        return

    record = {
        "source": source_string,
        "decision": decision,
        "timestamp": _now_ms(),
    }
    if isinstance(tool_use_context, dict):
        decisions = tool_use_context.setdefault("toolDecisions", {})
        decisions[tool_use_id] = record
    else:
        decisions = getattr(tool_use_context, "toolDecisions", None)
        if decisions is None:
            decisions = {}
            setattr(tool_use_context, "toolDecisions", decisions)
        decisions[tool_use_id] = record


def logPermissionCheck(toolName: str, allowed: bool, reason: str = "") -> None:
    decision = "accept" if allowed else "reject"
    source = {"type": "hook"}
    logPermissionDecision(
        {
            "tool": {"name": toolName},
            "toolUseContext": {},
            "messageId": None,
            "toolUseID": toolName,
        },
        {"decision": decision, "source": source},
    )
    if reason:
        LOGGER.info("tool_permission_reason tool=%s reason=%s", toolName, reason)


def _tool_name(tool: Any) -> str:
    if isinstance(tool, dict):
        return str(tool.get("name", "unknown"))
    return str(getattr(tool, "name", "unknown"))


def _now_ms() -> int:
    import time

    return int(time.time() * 1000)


log_permission_check = logPermissionCheck
is_code_editing_tool = isCodeEditingTool
build_code_edit_tool_attributes = buildCodeEditToolAttributes
log_permission_decision = logPermissionDecision

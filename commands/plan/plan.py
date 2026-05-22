"""plan command — mirrors src/commands/plan/plan.tsx.

Toggle plan mode: AI plans before executing, no tools run automatically.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...types import PermissionMode

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def planModeMessage(enabled: bool) -> str:
    return f"Plan mode: {'ON' if enabled else 'OFF'} (next request will be planned, not executed)"


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    current = False
    try:
        current = getattr(context, "permission_mode", PermissionMode.DEFAULT) == PermissionMode.PLAN
    except Exception:
        try:
            current = getattr(context, "config", {}).get("plan_mode", False)
        except Exception:
            pass
    new_state = not current

    try:
        setattr(context, "permission_mode", PermissionMode.PLAN if new_state else PermissionMode.DEFAULT)
    except Exception:
        pass

    try:
        tui = getattr(context, "_tui", None)
        if tui is not None:
            if hasattr(tui, "toggle_plan"):
                tui.toggle_plan()
            if hasattr(tui, "set_permission_mode"):
                tui.set_permission_mode(PermissionMode.PLAN if new_state else PermissionMode.DEFAULT)
    except Exception:
        pass

    try:
        if hasattr(context, "set_setting"):
            context.set_setting("plan_mode", new_state)
    except Exception:
        pass

    return TextResult(planModeMessage(new_state))


plan_mode_message = planModeMessage

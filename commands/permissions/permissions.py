"""permissions command — mirrors src/commands/permissions/permissions.tsx.

Configure tool permission modes: default, acceptEdits, bypassPermissions, plan.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult

PERMISSION_MODES = ["default", "acceptEdits", "bypassPermissions", "plan"]


def showPermissions(mode: str) -> str:
    """Show current permission mode."""
    descriptions = {
        "default": "Ask before running tools",
        "acceptEdits": "Auto-accept file edits, ask for others",
        "bypassPermissions": "Run all tools without asking",
        "plan": "Plan-only mode — no tool execution",
    }
    desc = descriptions.get(mode, "")
    return f"Permission mode: {mode}" + (f" — {desc}" if desc else "")


async def call(args: str, context: CommandContext) -> TextResult:
    """View or change permission mode."""
    from ...types.command import TextResult
    from ...types import PermissionMode

    mode = args.strip() if args else ""

    if not mode:
        current = "default"
        try:
            runtime_mode = getattr(context, "permission_mode", None)
            if runtime_mode is not None:
                current = getattr(runtime_mode, "value", runtime_mode)
            else:
                current = getattr(context, "config", {}).get("permission_mode", "default")
        except Exception:
            pass
        lines = [showPermissions(current), "", "Available modes:"]
        for m in PERMISSION_MODES:
            marker = " ← current" if m == current else ""
            lines.append(f"  /permissions {m}{marker}")
        return TextResult("\n".join(lines))

    if mode not in PERMISSION_MODES:
        return TextResult(f"Unknown mode: {mode}. Use: {', '.join(PERMISSION_MODES)}")

    try:
        if hasattr(context, "permission_mode"):
            context.permission_mode = PermissionMode(mode)

        engine = getattr(context, "_engine", None)
        if engine is not None and hasattr(engine, "permission_mode"):
            engine.permission_mode = PermissionMode(mode)

        if hasattr(context, "set_setting"):
            context.set_setting("permission_mode", mode)
    except Exception:
        pass

    return TextResult(showPermissions(mode))


show_permissions = showPermissions

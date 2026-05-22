"""hooks command — mirrors src/commands/hooks/hooks.tsx.

Manage hook scripts that run before/after tool calls and events.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult

HOOK_EVENTS = [
    "PreToolUse", "PostToolUse", "Notification",
    "UserPromptSubmit", "Stop", "SubagentStop",
]


def showHooks(config: dict | None = None) -> str:
    """Show configured hooks."""
    if not config or not config.get("hooks"):
        return "No hooks configured. Use /hooks add <event> <command> to add one."
    lines = ["Configured hooks:", ""]
    for event, cmd in config.get("hooks", {}).items():
        lines.append(f"  {event}: {cmd}")
    return "\n".join(lines)


async def call(args: str, context: CommandContext) -> TextResult:
    """View or manage hooks."""
    from ...types.command import TextResult

    parts = args.strip().split(maxsplit=2) if args.strip() else []
    action = parts[0].lower() if parts else ""

    cfg = {}
    try:
        cfg = getattr(context, "config", {}) or {}
    except Exception:
        pass

    if not action:
        return TextResult(showHooks(cfg))

    if action == "add" and len(parts) >= 3:
        event, cmd = parts[1], parts[2]
        if event not in HOOK_EVENTS:
            return TextResult(f"Unknown event: {event}. Valid: {', '.join(HOOK_EVENTS)}")
        hooks = cfg.get("hooks", {})
        hooks[event] = cmd
        try:
            if hasattr(context, "set_setting"):
                context.set_setting("hooks", hooks)
        except Exception:
            pass
        return TextResult(f"Hook added: {event} → {cmd}")

    if action == "remove" and len(parts) >= 2:
        event = parts[1]
        hooks = cfg.get("hooks", {})
        if event in hooks:
            del hooks[event]
            try:
                if hasattr(context, "set_setting"):
                    context.set_setting("hooks", hooks)
            except Exception:
                pass
            return TextResult(f"Hook removed: {event}")
        return TextResult(f"No hook for event: {event}")

    if action == "list":
        return TextResult(f"Available events: {', '.join(HOOK_EVENTS)}")

    return TextResult("Usage: /hooks [add <event> <cmd> | remove <event> | list]")


show_hooks = showHooks

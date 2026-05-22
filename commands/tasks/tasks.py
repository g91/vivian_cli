"""tasks command — mirrors src/commands/tasks/tasks.tsx.

Shows running background tasks and their status.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult

    try:
        app_state = getattr(context, "app_state", None)
        if app_state is None:
            state_store = getattr(context, "state_store", None)
            if state_store is None:
                qe = getattr(context, "query_engine", None)
                state_store = getattr(qe, "state_store", None) if qe is not None else None
            if state_store is not None and hasattr(state_store, "get_state"):
                app_state = state_store.get_state()

        tasks = {}
        if isinstance(app_state, dict):
            tasks = app_state.get("tasks", {}) or {}
        elif app_state is not None:
            tasks = getattr(app_state, "tasks", {}) or {}

        if tasks:
            lines = ["Active Tasks:", ""]
            iterable = tasks.values() if isinstance(tasks, dict) else tasks
            for t in iterable:
                if isinstance(t, dict):
                    tid = t.get("id", "?")
                    status = t.get("status", "?")
                    desc = t.get("description", "")
                else:
                    tid = getattr(t, "id", "?")
                    status = getattr(t, "status", "?")
                    desc = getattr(t, "description", "")
                lines.append(f"  [{status}] {tid}: {str(desc)[:60]}")
            return TextResult("\n".join(lines))
    except Exception:
        pass
    return TextResult("No active tasks.")


showTasks = call
show_tasks = call

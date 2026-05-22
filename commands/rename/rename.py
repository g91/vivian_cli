"""rename command — mirrors src/commands/rename/rename.ts.

Renames the current session with a user-provided name or auto-generates one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def generateSessionName(first_prompt: str = "") -> str:
    """Generate a short session name from the first prompt."""
    if not first_prompt:
        return "Untitled session"
    # Take first ~40 chars, truncate at word boundary
    name = first_prompt.strip()[:50]
    if len(first_prompt) > 50:
        name = name.rsplit(" ", 1)[0] + "..."
    return name


async def call(args: str, context: CommandContext) -> TextResult:
    """Rename the current session."""
    from ...types.command import TextResult

    new_name = args.strip() if args else ""

    if not new_name:
        # Auto-generate from first user message
        try:
            qe = getattr(context, "query_engine", None)
            if qe:
                msgs = getattr(qe, "messages", []) or []
                first_user = next((m for m in msgs if getattr(m, "role", "") == "user"), None)
                if first_user:
                    new_name = generateSessionName(getattr(first_user, "content", ""))
        except Exception:
            pass

    if not new_name:
        new_name = "Untitled session"

    # Store the name
    try:
        app_state = getattr(context, "app_state", None)
        if app_state:
            app_state.session_name = new_name
    except Exception:
        pass

    return TextResult(f"Session renamed to: {new_name}")


renameSession = call
rename_session = call
generate_session_name = generateSessionName

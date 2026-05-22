"""clear command — mirrors src/commands/clear/clear.ts."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    """Clear the current conversation state."""
    from ...types.command import TextResult
    from ...bootstrap.state import getSessionId, regenerateSessionId

    del args

    query_engine = getattr(context, "query_engine", None)
    if query_engine is not None:
        try:
            if hasattr(query_engine, "messages"):
                query_engine.messages.clear()
            if hasattr(query_engine, "_last_transcript_uuid"):
                query_engine._last_transcript_uuid = None
            if hasattr(query_engine, "_current_turn_user_uuid"):
                query_engine._current_turn_user_uuid = None
            if hasattr(query_engine, "_discovered_skill_names"):
                query_engine._discovered_skill_names.clear()
        except Exception:
            pass

    previous_session_id = getSessionId()
    next_session_id = regenerateSessionId({"setCurrentAsParent": True})

    if query_engine is not None:
        try:
            if hasattr(query_engine, "session_id"):
                query_engine.session_id = str(next_session_id)
        except Exception:
            pass

    try:
        state_store = getattr(context, "state_store", None)
        if state_store is not None and hasattr(state_store, "set_state"):
            state_store.set_state(
                lambda current: {
                    **current,
                    "standaloneAgentContext": None,
                    "sessionId": next_session_id,
                    "parentSessionId": previous_session_id,
                }
            )
    except Exception:
        pass

    return TextResult("")


async def _clear_screen(context: CommandContext) -> TextResult:
    return await call("", context)


async def _clear_caches(context: CommandContext) -> TextResult:
    return await call("", context)


async def _clear_conversation(context: CommandContext) -> TextResult:
    return await call("", context)


# Backward-compat aliases
clearScreen = _clear_screen
clearConversation = _clear_conversation
clearCaches = _clear_caches
clear_screen = _clear_screen
clear_conversation = _clear_conversation
clear_caches = _clear_caches

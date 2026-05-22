"""Away summary generation — mirrors src/services/awaySummary.ts."""
from __future__ import annotations

import asyncio
from typing import Optional

RECENT_MESSAGE_WINDOW = 30


def _build_away_summary_prompt(memory: Optional[str]) -> str:
    memory_block = f"Session memory (broader context):\n{memory}\n\n" if memory else ""
    return (
        f"{memory_block}The user stepped away and is coming back. Write exactly 1-3 short sentences. "
        "Start by stating the high-level task — what they are building or debugging, not implementation details. "
        "Next: the concrete next step. Skip status reports and commit recaps."
    )


async def generateAwaySummary(
    messages: list,
    signal: Optional[asyncio.Event] = None,
) -> Optional[str]:
    """Generate a short session recap for the 'while you were away' card.

    Returns None on abort, empty transcript, or error.
    Mirrors generateAwaySummary() from awaySummary.ts.
    """
    if not messages:
        return None

    try:
        from .SessionMemory.sessionMemoryUtils import getSessionMemoryContent
        from ..utils.debug import logForDebugging
        from ..utils.messages import createUserMessage, getAssistantMessageText
        from ..utils.model.model import getSmallFastModel
        from ..utils.systemPromptType import asSystemPrompt
        from .api.vivian import queryModelWithoutStreaming

        memory = await getSessionMemoryContent()
        recent = list(messages[-RECENT_MESSAGE_WINDOW:])
        recent.append(createUserMessage({"content": _build_away_summary_prompt(memory)}))
        response = await queryModelWithoutStreaming({
            "messages": recent,
            "systemPrompt": asSystemPrompt([]),
            "thinkingConfig": {"type": "disabled"},
            "tools": [],
            "signal": signal,
            "options": {
                "model": getSmallFastModel(),
                "toolChoice": None,
                "isNonInteractiveSession": False,
                "hasAppendSystemPrompt": False,
                "agents": [],
                "querySource": "away_summary",
                "mcpTools": [],
                "skipCacheWrite": True,
            },
        })
        if response.get("isApiErrorMessage"):
            logForDebugging(f"[awaySummary] API error: {getAssistantMessageText(response)}")
            return None
        return getAssistantMessageText(response)
    except asyncio.CancelledError:
        return None
    except Exception as err:
        try:
            from ..utils.debug import logForDebugging

            logForDebugging(f"[awaySummary] generation failed: {err}")
        except Exception:
            pass
        return None


generate_away_summary = generateAwaySummary

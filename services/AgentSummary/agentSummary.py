"""Agent summary service — mirrors src/services/AgentSummary/agentSummary.ts."""
from __future__ import annotations

import asyncio
from typing import Optional

SUMMARY_INTERVAL_MS = 30_000


def _build_summary_prompt(previous_summary: Optional[str]) -> str:
    prev_line = f'\nPrevious: "{previous_summary}" — say something NEW.\n' if previous_summary else ""
    return (
        f"Describe your most recent action in 3-5 words using present tense (-ing). "
        f"Name the file or function, not the branch. Do not use tools.\n{prev_line}\n"
        "Good: \"Reading runAgent.ts\"\n"
        "Good: \"Fixing null check in validate.ts\"\n"
        "Bad (too vague): \"Investigating the issue\""
    )


async def generateAgentSummary(
    agent_id: str,
    messages: list[dict],
    previous_summary: Optional[str] = None,
    signal: Optional[asyncio.Event] = None,
) -> Optional[str]:
    """Generate a periodic background summary for a sub-agent.

    Mirrors generateAgentSummary() from agentSummary.ts.
    """
    if not messages:
        return None

    try:
        from ..api.vivian import queryModelWithoutStreaming
        from ...utils.model.model import getSmallFastModel

        prompt = _build_summary_prompt(previous_summary)
        response = await queryModelWithoutStreaming({
            "messages": [{"role": "user", "content": prompt}],
            "systemPrompt": [],
            "thinkingConfig": {"type": "disabled"},
            "tools": [],
            "signal": signal,
            "options": {
                "model": getSmallFastModel(),
                "querySource": "agent_summary",
                "isNonInteractiveSession": True,
                "hasAppendSystemPrompt": False,
                "agents": [],
                "mcpTools": [],
            },
        })
        return response.get("text", "").strip() or None
    except Exception:
        return None


generate_agent_summary = generateAgentSummary

"""Tool use summary generator — mirrors src/services/toolUseSummary/toolUseSummaryGenerator.ts."""
from __future__ import annotations

import asyncio
import json
from typing import Optional

TOOL_USE_SUMMARY_SYSTEM_PROMPT = """Write a short summary label describing what these tool calls accomplished. It appears as a single-line row in a mobile app and truncates around 30 characters, so think git-commit-subject, not sentence.

Keep the verb in past tense and the most distinctive noun. Drop articles, connectors, and long location context first.

Examples:
- Searched in auth/
- Fixed NPE in UserService
- Created signup endpoint
- Read config.json
- Ran failing tests"""


def truncateJson(value: object, max_length: int) -> str:
    """Truncate a JSON value to a maximum length for the prompt.

    Mirrors truncateJson() from toolUseSummaryGenerator.ts.
    """
    try:
        s = json.dumps(value, default=str)
        if len(s) <= max_length:
            return s
        return s[:max_length - 3] + "..."
    except Exception:
        return "[unable to serialize]"


async def generateToolUseSummary(
    tools: list[dict],
    signal: Optional[asyncio.Event] = None,
    is_non_interactive_session: bool = False,
    last_assistant_text: Optional[str] = None,
) -> Optional[str]:
    """Generate a human-readable summary of completed tools.

    Mirrors generateToolUseSummary() from toolUseSummaryGenerator.ts.
    """
    if not tools:
        return None

    try:
        from ..api.vivian import queryModelWithoutStreaming
        from ...utils.model.model import getSmallFastModel

        tool_summaries = "\n\n".join(
            f"Tool: {t['name']}\nInput: {truncateJson(t.get('input'), 300)}\nOutput: {truncateJson(t.get('output'), 300)}"
            for t in tools
        )
        context_prefix = (
            f"User's intent (from assistant's last message): {last_assistant_text[:200]}\n\n"
            if last_assistant_text
            else ""
        )
        user_prompt = f"{context_prefix}Tools completed:\n\n{tool_summaries}\n\nLabel:"

        response = await queryModelWithoutStreaming({
            "messages": [{"role": "user", "content": user_prompt}],
            "systemPrompt": [{"type": "text", "text": TOOL_USE_SUMMARY_SYSTEM_PROMPT}],
            "thinkingConfig": {"type": "disabled"},
            "tools": [],
            "signal": signal,
            "options": {
                "model": getSmallFastModel(),
                "querySource": "tool_use_summary_generation",
                "isNonInteractiveSession": is_non_interactive_session,
                "hasAppendSystemPrompt": False,
                "agents": [],
                "mcpTools": [],
            },
        })

        summary = response.get("text", "").strip()
        return summary or None
    except Exception:
        return None


generate_tool_use_summary = generateToolUseSummary
truncate_json = truncateJson

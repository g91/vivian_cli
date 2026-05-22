"""
Port of src/utils/sessionTitle.ts
"""
from __future__ import annotations

from typing import Any
import json

from ..bootstrap.state import getIsNonInteractiveSession
from ..services.analytics.index import logEvent
from ..services.api.vivian import queryModelWithoutStreaming
from .debug import logForDebugging
from .model.model import getSmallFastModel


MAX_CONVERSATION_TEXT = 1000
SESSION_TITLE_PROMPT = """Generate a concise, sentence-case title (3-7 words) that captures the main topic or goal of this coding session. The title should be clear enough that the user recognizes the session in a list. Use sentence case: capitalize only the first word and proper nouns.

Return JSON with a single \"title\" field.

Good examples:
{\"title\": \"Fix login button on mobile\"}
{\"title\": \"Add OAuth authentication\"}
{\"title\": \"Debug failing CI tests\"}
{\"title\": \"Refactor API client error handling\"}

Bad (too vague): {\"title\": \"Code changes\"}
Bad (too long): {\"title\": \"Investigate and fix the issue where the login button does not respond on mobile devices\"}
Bad (wrong case): {\"title\": \"Fix Login Button On Mobile\"}"""


def _message_content(message: Any) -> Any:
    if isinstance(message, dict):
        nested = message.get("message")
        if isinstance(nested, dict) and "content" in nested:
            return nested.get("content")
        if "content" in message:
            return message.get("content")
    return None


def _extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "".join(parts)
    return ""


def extractConversationText(messages: list[Any]) -> str:
    """Flatten a message array into a single text string for Haiku title input.
Skips meta/non-human messages. Tail-slices to the last 1000 chars so
recent context wins when the conversation is long."""
    parts: list[str] = []
    for msg in messages or []:
        if not isinstance(msg, dict):
            continue
        msg_type = msg.get("type") or msg.get("role")
        if msg_type not in ("user", "assistant"):
            continue
        if msg.get("isMeta"):
            continue
        origin = msg.get("origin")
        if isinstance(origin, dict) and origin.get("kind") not in (None, "human"):
            continue
        text = _extract_text_content(_message_content(msg))
        if text:
            parts.append(text)
    text = "\n".join(parts)
    return text[-MAX_CONVERSATION_TEXT:] if len(text) > MAX_CONVERSATION_TEXT else text


async def generateSessionTitle(description: str, signal: Any = None) -> str | None:
    """Generate a sentence-case session title from a description or first message.
Returns null on error or if Haiku returns an unparseable response.

@param description - The user's first message or a description of the session
@param signal - Abort signal for cancellation"""
    trimmed = (description or "").strip()
    if not trimmed:
        return None

    try:
        result = await queryModelWithoutStreaming(
            {
                "messages": [{"role": "user", "content": trimmed}],
                "systemPrompt": [{"type": "text", "text": SESSION_TITLE_PROMPT}],
                "signal": signal,
                "options": {
                    "model": getSmallFastModel(),
                    "querySource": "generate_session_title",
                    "agents": [],
                    "isNonInteractiveSession": getIsNonInteractiveSession(),
                    "hasAppendSystemPrompt": False,
                    "mcpTools": [],
                },
            }
        )

        text = _extract_text_content(result.get("message", {}).get("content")) or result.get("text", "")
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            logEvent("tengu_session_title_generated", {"success": False})
            return None
        parsed = json.loads(text[start : end + 1])
        title = str(parsed.get("title", "")).strip() or None
        logEvent("tengu_session_title_generated", {"success": title is not None})
        return title
    except Exception as error:
        logForDebugging(f"generateSessionTitle failed: {error}", level="error")
        logEvent("tengu_session_title_generated", {"success": False})
        return None


extract_conversation_text = extractConversationText
generate_session_title = generateSessionTitle


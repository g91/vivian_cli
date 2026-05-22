"""Port of src/utils/processUserInput/processTextPrompt.ts."""
from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from ...bootstrap.state import setPromptId
from ...services.analytics.index import logEvent
from ..messages import createUserMessage
from ..telemetry.events import logOTelEvent, redactIfDisabled
from ..telemetry.sessionTracing import startInteractionSpan
from ..userPromptKeywords import matches_keep_going_keyword, matches_negative_keyword


def _find_text_block(blocks: list[dict[str, Any]], reverse: bool = False) -> str:
    iterator = reversed(blocks) if reverse else blocks
    for block in iterator:
        if isinstance(block, dict) and block.get("type") == "text":
            return str(block.get("text", ""))
    return ""


def processTextPrompt(
    input: str | list[dict[str, Any]],
    imageContentBlocks: list[dict[str, Any]],
    imagePasteIds: list[int],
    attachmentMessages: list[Any],
    uuid: str | None = None,
    permissionMode: Any = None,
    isMeta: bool | None = None,
):
    prompt_id = str(uuid4())
    setPromptId(prompt_id)

    user_prompt_text = input if isinstance(input, str) else _find_text_block(input)
    startInteractionSpan(user_prompt_text)

    otel_prompt_text = input if isinstance(input, str) else _find_text_block(input, reverse=True)
    if otel_prompt_text:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                logOTelEvent(
                    "user_prompt",
                    {
                        "prompt_length": str(len(otel_prompt_text)),
                        "prompt": redactIfDisabled(otel_prompt_text),
                        "prompt.id": prompt_id,
                    },
                )
            )
        except RuntimeError:
            _telemetry_scheduled = False

    is_negative = matches_negative_keyword(user_prompt_text)
    is_keep_going = matches_keep_going_keyword(user_prompt_text)
    logEvent(
        "tengu_input_prompt",
        {
            "is_negative": is_negative,
            "is_keep_going": is_keep_going,
        },
    )

    if imageContentBlocks:
        text_content = []
        if isinstance(input, str):
            if input.strip():
                text_content = [{"type": "text", "text": input}]
        else:
            text_content = input

        user_message = createUserMessage(
            {
                "content": [*text_content, *imageContentBlocks],
                "uuid": uuid,
                "imagePasteIds": imagePasteIds or None,
                "permissionMode": permissionMode,
                "isMeta": isMeta or None,
            }
        )
        return {
            "messages": [user_message, *attachmentMessages],
            "shouldQuery": True,
        }

    user_message = createUserMessage(
        {
            "content": input,
            "uuid": uuid,
            "permissionMode": permissionMode,
            "isMeta": isMeta or None,
        }
    )
    return {
        "messages": [user_message, *attachmentMessages],
        "shouldQuery": True,
    }
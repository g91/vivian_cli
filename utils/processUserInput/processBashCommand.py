"""Port of src/utils/processUserInput/processBashCommand.tsx."""
from __future__ import annotations

from ..messages import createUserMessage


async def processBashCommand(inputString, precedingInputBlocks, attachmentMessages, context, setToolJSX):
    del context, setToolJSX
    content = list(precedingInputBlocks or [])
    content.append({"type": "text", "text": inputString})
    return {
        "messages": [createUserMessage({"content": content}), *(attachmentMessages or [])],
        "shouldQuery": True,
    }
"""Extract memories service — mirrors src/services/extractMemories/extractMemories.ts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional


def initExtractMemories() -> Callable:
    """Initialize the extract memories service closure.

    Mirrors initExtractMemories() from extractMemories.ts.
    Returns an async function that extracts memories from messages.
    """
    last_extracted_id: Optional[str] = None

    async def extract_memories(messages: list, context: dict) -> None:
        nonlocal last_extracted_id
        try:
            from ...memdir.paths import get_memory_dir, is_auto_memory_enabled
        except Exception:
            return

        if not is_auto_memory_enabled() or not messages:
            return

        start_index = 0
        if last_extracted_id is not None:
            for index, message in enumerate(messages):
                if message.get("uuid") == last_extracted_id:
                    start_index = index + 1
                    break

        new_messages = messages[start_index:]
        if not new_messages:
            return

        user_texts: list[str] = []
        for message in new_messages:
            if message.get("type") != "user":
                continue
            content = message.get("message") or message.get("content") or message.get("text")
            if isinstance(content, str) and content.strip():
                user_texts.append(content.strip())
            elif isinstance(content, list):
                text_chunks = [block.get("text", "") for block in content if isinstance(block, dict)]
                joined = "\n".join(chunk for chunk in text_chunks if chunk)
                if joined.strip():
                    user_texts.append(joined.strip())

        if not user_texts:
            last_extracted_id = new_messages[-1].get("uuid", last_extracted_id)
            return

        memory_dir = Path(get_memory_dir())
        memory_dir.mkdir(parents=True, exist_ok=True)
        memory_file = memory_dir / "MEMORY.md"
        session_id = context.get("sessionId") or context.get("session_id") or "unknown-session"
        payload = {
            "session": session_id,
            "messages": user_texts[-5:],
        }
        block = "\n".join(
            [
                "## Extracted session memory",
                "",
                "```json",
                json.dumps(payload, indent=2, ensure_ascii=True),
                "```",
                "",
            ]
        )
        existing = memory_file.read_text(encoding="utf-8") if memory_file.exists() else "# Memory\n\n"
        if block not in existing:
            memory_file.write_text(existing + block, encoding="utf-8")

        last_extracted_id = new_messages[-1].get("uuid", last_extracted_id)

    return extract_memories


init_extract_memories = initExtractMemories

"""Find relevant memories — mirrors src/memdir/findRelevantMemories.ts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .memory_scan import MemoryHeader, format_memory_manifest, scan_memory_files

SELECT_MEMORIES_SYSTEM_PROMPT = (
    "You are selecting memories that will be useful to vivian Code as it processes "
    "a user's query. You will be given the user's query and a list of available memory "
    "files with their filenames and descriptions.\n\n"
    "Return a JSON array of filenames for the memories that will clearly be useful to "
    "vivian Code as it processes the user's query (up to 5). Only include memories that "
    "you are certain will be helpful based on their name and description.\n"
    "- If you are unsure if a memory will be useful in processing the user's query, "
    "then do not include it in your list. Be selective and discerning.\n"
    "- If there are no memories in the list that would clearly be useful, return [].\n"
    "- If a list of recently-used tools is provided, do not select memories that are "
    "usage reference or API documentation for those tools. DO still select memories "
    "containing warnings, gotchas, or known issues about those tools."
)


class RelevantMemory:
    def __init__(self, path: str, mtime_ms: float) -> None:
        self.path = path
        self.mtime_ms = mtime_ms


async def find_relevant_memories(
    query: str,
    memory_dir: str,
    _signal=None,
    recent_tools: tuple = (),
    already_surfaced: Optional[set] = None,
) -> list[RelevantMemory]:
    """Ask a side query to pick up to 5 relevant memory files."""
    already_surfaced = already_surfaced or set()
    all_headers = scan_memory_files(memory_dir)
    memories = [m for m in all_headers if m.file_path not in already_surfaced]
    if not memories:
        return []

    manifest = format_memory_manifest(memories)
    tools_note = ""
    if recent_tools:
        tools_note = f"\nRecently used tools: {', '.join(recent_tools)}"

    try:
        selected_filenames = await _select_relevant_memories(
            query, manifest, tools_note
        )
    except Exception:
        return []

    by_filename = {m.filename: m for m in memories}
    selected: list[RelevantMemory] = []
    for fname in selected_filenames:
        h = by_filename.get(fname)
        if h:
            selected.append(RelevantMemory(path=h.file_path, mtime_ms=h.mtime_ms))
    return selected


async def _select_relevant_memories(
    query: str, manifest: str, tools_note: str
) -> list[str]:
    """Use a side model call to select relevant filenames.  Returns filename list."""
    try:
        import httpx
        import os

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return []

        prompt = (
            f"User query:\n{query}\n\n"
            f"Available memory files:\n{manifest}"
            f"{tools_note}\n\n"
            "Return a JSON array of filenames (strings) to load. Example: "
            '["debugging.md","patterns.md"]'
        )
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api-vivian.d0a.net/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "vivian-haiku-4-5",
                    "max_tokens": 256,
                    "system": SELECT_MEMORIES_SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            text = resp.json()["content"][0]["text"].strip()
            # Extract JSON array
            start = text.find("[")
            end = text.rfind("]")
            if start == -1 or end == -1:
                return []
            return json.loads(text[start : end + 1])
    except Exception:
        return []

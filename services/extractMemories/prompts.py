"""Extract memories prompts — mirrors src/services/extractMemories/prompts.ts."""
from __future__ import annotations


def buildExtractAutoOnlyPrompt(new_message_count: int, existing_memories: str) -> str:
    """Build prompt for auto-only memory extraction."""
    return (
        f"Extract {new_message_count} new messages and existing memories:\n\n"
        f"{existing_memories}"
    )


def buildExtractPrompt(new_message_count: int, existing_memories: str) -> str:
    """Build prompt for full memory extraction."""
    return buildExtractAutoOnlyPrompt(new_message_count, existing_memories)


build_extract_auto_only_prompt = buildExtractAutoOnlyPrompt
build_extract_prompt = buildExtractPrompt

"""MagicDocs prompts — mirrors src/services/MagicDocs/prompts.ts."""
from __future__ import annotations


def buildMagicDocsUpdatePrompt(title: str, current_content: str, conversation_context: str) -> str:
    """Build the prompt for magic docs update.

    Mirrors buildMagicDocsUpdatePrompt() from prompts.ts.
    """
    return (
        f"Update this MAGIC DOC titled '{title}' based on new learnings from the conversation.\n\n"
        f"Current content:\n{current_content}\n\n"
        f"Conversation context:\n{conversation_context}"
    )


build_magic_docs_update_prompt = buildMagicDocsUpdatePrompt

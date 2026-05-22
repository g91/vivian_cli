"""Prompt cache — mirrors src/hooks/usePromptCache.ts."""
from __future__ import annotations

def usePromptCache() -> dict:
    """Cache prompt templates."""
    return {"cache": {}}

use_prompt_cache = usePromptCache

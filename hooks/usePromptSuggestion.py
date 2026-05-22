"""Prompt suggestion hook — mirrors src/hooks/usePromptSuggestion.ts."""
from __future__ import annotations
from typing import Any

def usePromptSuggestion(suggestions: list[str] | None = None) -> dict[str, Any]:
    """Manage prompt auto-suggestions."""
    return {
        'suggestions': suggestions or [],
        'selected': None,
    }

use_prompt_suggestion = usePromptSuggestion

"""
Port of src/utils/systemPromptType.ts
"""
from __future__ import annotations

from typing import Iterable, List, NewType


"""Branded type for system prompt arrays.

This module is intentionally dependency-free so it can be imported
from anywhere without risking circular initialization issues.
"""

SystemPrompt = NewType("SystemPrompt", List[str])


def asSystemPrompt(value: Iterable[str]) -> SystemPrompt:
    return SystemPrompt(list(value))


as_system_prompt = asSystemPrompt

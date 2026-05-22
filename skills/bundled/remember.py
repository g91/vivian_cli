"""Remember skill — mirrors src/skills/bundled/remember.ts."""
from __future__ import annotations

import os
from typing import Any

from ..bundled_skills import BundledSkillDefinition, register_bundled_skill

_SKILL_PROMPT = """# Memory Review

## Goal
Review the user's memory landscape and produce a clear report of proposed changes, grouped by action type. Do NOT apply changes — present proposals for user approval.

## Steps

### 1. Gather all memory layers
Read vivian.md and vivian.local.md from the project root (if they exist). Review auto-memory content already in your system prompt. Note which team memory sections exist, if any.

### 2. Classify each auto-memory entry
For each substantive entry in auto-memory, determine the best destination:

| Destination | What belongs there |
|---|---|
| **vivian.md** | Project conventions all contributors should follow |
| **vivian.local.md** | Personal instructions specific to this user |
| **Stay in auto-memory** | Working notes, temporary context |

### 3. Identify cleanup opportunities
Scan for: Duplicates, Outdated entries, Conflicts.

### 4. Present the report
Output a structured report grouped by action type:
1. **Promotions** — entries to move, with destination and rationale
2. **Cleanup** — duplicates, outdated entries, conflicts
3. **Ambiguous** — entries where you need the user's input
4. **No action needed** — brief note on entries that should stay put

## Rules
- Present ALL proposals before making any changes
- Do NOT modify files without explicit user approval
"""


def register_remember_skill() -> None:
    if os.environ.get("USER_TYPE") != "ant":
        return

    register_bundled_skill(BundledSkillDefinition(
        name="remember",
        description="Review and organize memories across all layers.",
        user_invocable=True,
        get_prompt_for_command=lambda args="", ctx=None: [
            {"type": "text", "text": _SKILL_PROMPT}
        ],
    ))

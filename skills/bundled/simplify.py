"""Simplify skill — mirrors src/skills/bundled/simplify.ts."""
from __future__ import annotations

from typing import Any

from ..bundled_skills import BundledSkillDefinition, register_bundled_skill

_SIMPLIFY_PROMPT = """# Simplify: Code Review and Cleanup

Review all changed files for reuse, quality, and efficiency. Fix any issues found.

## Phase 1: Identify Changes

Run `git diff` (or `git diff HEAD` if there are staged changes) to see what changed. If there are no git changes, review the most recently modified files that the user mentioned or that you edited earlier in this conversation.

## Phase 2: Launch Three Review Agents in Parallel

Use the Agent tool to launch all three agents concurrently in a single message. Pass each agent the full diff so it has the complete context.

### Agent 1: Code Reuse Review

For each change:
1. Search for existing utilities and helpers that could replace newly written code.
2. Flag any new function that duplicates existing functionality.
3. Flag any inline logic that could use an existing utility.

### Agent 2: Code Quality Review

Review the same changes for hacky patterns:
1. Redundant state
2. Parameter sprawl
3. Copy-paste with slight variation
4. Leaky abstractions
5. Stringly-typed code
6. Unnecessary nesting
7. Unnecessary comments

### Agent 3: Efficiency Review

Review the same changes for efficiency:
1. Unnecessary work
2. Missed concurrency
3. Hot-path bloat
4. Recurring no-op updates
5. Memory leaks or unbounded structures
6. Overly broad operations

## Phase 3: Fix Issues

Wait for all three agents to complete. Aggregate their findings and fix each issue directly. If a finding is a false positive or not worth addressing, note it and move on.

When done, briefly summarize what was fixed (or confirm the code was already clean).
"""


def register_simplify_skill() -> None:
    register_bundled_skill(BundledSkillDefinition(
        name="simplify",
        description="Review changed code for reuse, quality, and efficiency, then fix any issues found.",
        user_invocable=True,
        get_prompt_for_command=lambda args="", ctx=None: [
            {"type": "text", "text": _SIMPLIFY_PROMPT}
        ],
    ))

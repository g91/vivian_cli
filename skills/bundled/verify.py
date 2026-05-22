"""Verify skill — mirrors src/skills/bundled/verify.ts."""
from __future__ import annotations

from typing import Any

from ..bundled_skills import BundledSkillDefinition, register_bundled_skill

_VERIFY_PROMPT = """# Verify: Correctness and Completeness Check

Verify that the task or implementation is correct, complete, and ready.

## Phase 1: Understand Requirements

Review what was asked:
1. Re-read the original user request.
2. List the explicit requirements.
3. List any implicit requirements or edge cases.

## Phase 2: Verify Implementation

For each requirement, check:
- ✅ Is it implemented?
- ✅ Is it implemented correctly?
- ✅ Are edge cases handled?
- ✅ Are there tests?

## Phase 3: Run Tests

If tests exist, run them. If tests fail, fix the issues.

## Phase 4: Report

Provide a verification report:
- **Passed**: Requirements that are fully met
- **Failed**: Requirements that are missing or broken (with fix)
- **Warnings**: Requirements that are partially met or have concerns

If everything passes, confirm the implementation is complete.
"""


def register_verify_skill() -> None:
    register_bundled_skill(BundledSkillDefinition(
        name="verify",
        description="Verify that a task or implementation is correct and complete.",
        user_invocable=True,
        get_prompt_for_command=lambda args="", ctx=None: [
            {"type": "text", "text": _VERIFY_PROMPT}
        ],
    ))

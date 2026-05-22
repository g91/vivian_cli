"""VerifyContent skill — mirrors src/skills/bundled/verifyContent.ts."""
from __future__ import annotations

from typing import Any

from ..bundled_skills import BundledSkillDefinition, register_bundled_skill

_VERIFY_CONTENT_PROMPT = """# VerifyContent: Review Content for Quality and Accuracy

Review the given content for quality, accuracy, and completeness.

## Checks

1. **Accuracy**: Is the information factually correct?
2. **Completeness**: Is anything important missing?
3. **Clarity**: Is the content easy to understand?
4. **Tone**: Is the tone appropriate for the audience?
5. **Format**: Is the formatting consistent and appropriate?

## Output

Provide:
- A summary verdict (Approved / Needs Revision)
- Specific issues found with line references
- Suggested corrections for each issue
"""


def register_verify_content_skill() -> None:
    register_bundled_skill(BundledSkillDefinition(
        name="verifyContent",
        description="Review content for quality, accuracy, and completeness.",
        user_invocable=True,
        get_prompt_for_command=lambda args="", ctx=None: [
            {"type": "text", "text": _VERIFY_CONTENT_PROMPT}
        ],
    ))

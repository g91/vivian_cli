"""Skillify skill — mirrors src/skills/bundled/skillify.ts."""
from __future__ import annotations

from typing import Any

from ..bundled_skills import BundledSkillDefinition, register_bundled_skill

_SKILLIFY_PROMPT = """# Skillify

You are capturing this session's repeatable process as a reusable skill.

## Your Task

### Step 1: Analyze the Session

Before asking any questions, analyze the session to identify:
- What repeatable process was performed
- What the inputs/parameters were
- The distinct steps (in order)
- What tools and permissions were needed

### Step 2: Interview the User

Use AskUserQuestion for ALL questions. For each round, iterate until the user is happy.

**Round 1: High level confirmation**
- Suggest a name and description for the skill based on your analysis.

**Round 2: Parameter confirmation**
- Identify the variable inputs (arguments to the skill).

**Round 3: Craft the skill**
- Draft the skill prompt.
- Ask the user to review it.

### Step 3: Save the Skill

Save the skill as a `.md` file in `~/.vivian/skills/` (user-global) or `.vivian/skills/` (project-local).
"""


def register_skillify_skill() -> None:
    register_bundled_skill(BundledSkillDefinition(
        name="skillify",
        description="Turn this conversation into a reusable skill.",
        user_invocable=True,
        get_prompt_for_command=lambda args="", ctx=None: [
            {"type": "text", "text": _SKILLIFY_PROMPT}
        ],
    ))

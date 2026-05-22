"""Batch skill — mirrors src/skills/bundled/batch.ts."""
from __future__ import annotations

from typing import Any

from ..bundled_skills import BundledSkillDefinition, register_bundled_skill

MIN_AGENTS = 5
MAX_AGENTS = 30

_BATCH_PROMPT = f"""# Batch: Parallel Work Orchestration

You are orchestrating a large, parallelizable change across this codebase.

## Phase 1: Research and Plan

1. **Understand the scope.** Launch subagents to deeply research what this instruction touches.
2. **Decompose into independent units.** Break the work into {MIN_AGENTS}–{MAX_AGENTS} self-contained units. Each unit must:
   - Be independently implementable
   - Be mergeable on its own
   - Be roughly uniform in size
3. **Determine the e2e test recipe.**
4. **Write the plan.**

## Phase 2: Spawn Workers (After Plan Approval)

After the plan is approved, spawn worker agents. Each worker should:
1. Implement the assigned change
2. Run tests
3. Commit and push
4. Create a PR
5. Report: `PR: <url>`

## Phase 3: Aggregate Results

Wait for all workers to report. Summarize:
- PRs created
- Any failures or blockers
- Next steps
"""


def register_batch_skill() -> None:
    register_bundled_skill(BundledSkillDefinition(
        name="batch",
        description="Orchestrate a large parallelizable change across the codebase using multiple agents.",
        user_invocable=True,
        get_prompt_for_command=lambda args="", ctx=None: [
            {"type": "text", "text": f"{_BATCH_PROMPT}\n\n## User Instruction\n\n{args}"}
        ],
    ))

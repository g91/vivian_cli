"""Stuck skill — mirrors src/skills/bundled/stuck.ts."""
from __future__ import annotations

from typing import Any

from ..bundled_skills import BundledSkillDefinition, register_bundled_skill

_STUCK_PROMPT = """/stuck — diagnose frozen/slow vivian Code sessions

The user thinks another vivian Code session on this machine is frozen, stuck, or very slow. Investigate and post a report.

## What to look for

Scan for other vivian Code processes (excluding the current one). Process names are typically `vivian` (installed) or `cli` (native dev build).

Signs of a stuck session:
- **High CPU (>=90%) sustained** — likely an infinite loop.
- **Process state `D` (uninterruptible sleep)** — often an I/O hang.
- **Process state `T` (stopped)** — user probably hit Ctrl+Z by accident.
- **Process state `Z` (zombie)** — parent isn't reaping.
- **Very high RSS (>=4GB)** — possible memory leak.
- **Stuck child process** — a hung `git`, `node`, or shell subprocess can freeze the parent.

## Investigation steps

1. List all vivian Code processes:
   ```
   ps -axo pid=,pcpu=,rss=,etime=,state=,comm=,command= | grep -E '(vivian|cli)' | grep -v grep
   ```

2. For anything suspicious, gather more context.

3. Check debug logs at `~/.vivian/debug/<session-id>.txt`.

## Report

Only post to Slack if you actually found something stuck. If every session looks healthy, tell the user directly.

## Notes
- Don't kill or signal any processes — this is diagnostic only.
"""


def register_stuck_skill() -> None:
    register_bundled_skill(BundledSkillDefinition(
        name="stuck",
        description="Diagnose frozen or slow vivian Code sessions.",
        argument_hint="[issue description]",
        user_invocable=True,
        get_prompt_for_command=lambda args="", ctx=None: [
            {"type": "text", "text": _STUCK_PROMPT}
        ],
    ))

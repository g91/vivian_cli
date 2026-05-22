"""Fork subagent feature — mirrors src/tools/AgentTool/forkSubagent.ts"""
from __future__ import annotations
import os


def isForkSubagentEnabled() -> bool:
    """Whether the fork-subagent feature is enabled."""
    val = os.environ.get("vivian_CODE_FORK_SUBAGENT", "")
    return val.lower() in ("1", "true", "yes")

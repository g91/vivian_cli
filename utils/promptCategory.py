"""Prompt category / query source helpers — mirrors src/utils/promptCategory.ts"""
from __future__ import annotations

from typing import Optional


def get_query_source_for_agent(
    agent_type: Optional[str],
    is_built_in_agent: bool,
) -> str:
    """Return the analytics query source string for an agent."""
    if is_built_in_agent:
        return f"agent:builtin:{agent_type}" if agent_type else "agent:default"
    return "agent:custom"


def get_query_source_for_repl() -> str:
    """Return the analytics query source string for a REPL session."""
    return "repl_main_thread"

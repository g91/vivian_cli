"""Built-in agent definitions — mirrors src/tools/AgentTool/builtInAgents.ts"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from .constants import VERIFICATION_AGENT_TYPE


def getBuiltInAgentDefinitions() -> List[Dict[str, Any]]:
    """Return the list of built-in agent definitions."""
    return [
        {
            "agentType": "Explore",
            "whenToUse": "Fast read-only codebase exploration and Q&A. Safe to call in parallel.",
            "tools": ["Read", "Glob", "Grep", "Bash"],
            "disallowedTools": ["Edit", "Write"],
        },
        {
            "agentType": "Plan",
            "whenToUse": "Create a structured implementation plan before writing code.",
            "tools": ["Read", "Glob", "Grep", "Bash", "EnterPlanMode", "ExitPlanMode"],
            "disallowedTools": [],
        },
        {
            "agentType": VERIFICATION_AGENT_TYPE,
            "whenToUse": "Verify correctness of an implementation by running tests and checks.",
            "tools": ["Read", "Bash", "Grep", "Glob"],
            "disallowedTools": [],
        },
        {
            "agentType": "general-purpose",
            "whenToUse": "General-purpose agent with access to all tools for complex multi-step tasks.",
            "tools": [],
            "disallowedTools": [],
        },
    ]

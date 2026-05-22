"""MCP skill builders — mirrors src/skills/mcpSkillBuilders.ts.

Write-once registry for the two loadSkillsDir functions that MCP skill
discovery needs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class MCPSkillBuilders:
    create_skill_command: Callable[..., dict]
    parse_skill_frontmatter_fields: Callable[[dict, str, str], dict]


_BUILDERS: Optional[MCPSkillBuilders] = None


def register_mcp_skill_builders(builders: MCPSkillBuilders) -> None:
    global _BUILDERS
    _BUILDERS = builders


def get_mcp_skill_builders() -> MCPSkillBuilders:
    if _BUILDERS is None:
        raise ValueError(
            "MCP skill builders not registered — load_skills_dir.py has not been evaluated yet"
        )
    return _BUILDERS

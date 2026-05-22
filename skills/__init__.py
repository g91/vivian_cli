"""Skills package — mirrors src/skills/."""
from .bundled_skills import BundledSkillDefinition, register_bundled_skill, get_bundled_skills, get_bundled_skill
from .mcp_skill_builders import MCPSkillBuilders, register_mcp_skill_builders, get_mcp_skill_builders
from .load_skills_dir import load_skills_dir
from .bundled import init_bundled_skills

# Backward compat
try:
    from .registry import SkillRegistry, register_all_skills, BUNDLED_SKILLS
except ImportError:
    pass

__all__ = [
    "BundledSkillDefinition", "register_bundled_skill", "get_bundled_skills", "get_bundled_skill",
    "MCPSkillBuilders", "register_mcp_skill_builders", "get_mcp_skill_builders",
    "load_skills_dir", "init_bundled_skills",
]

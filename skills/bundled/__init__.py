"""Bundled skills init — mirrors src/skills/bundled/index.ts."""
from __future__ import annotations

import os


def _feature(name: str) -> bool:
    val = os.environ.get(f"vivian_CODE_FEATURE_{name.upper()}", "")
    return val.lower() in ("1", "true", "yes")


def init_bundled_skills() -> None:
    """Register all bundled skill definitions.

    To add a new bundled skill:
    1. Create a new file in vivian_cli/skills/bundled/ (e.g., my_skill.py)
    2. Export a register function that calls register_bundled_skill()
    3. Import and call that function here
    """
    from .update_config import register_update_config_skill
    from .keybindings import register_keybindings_skill
    from .verify import register_verify_skill
    from .debug import register_debug_skill
    from .lorem_ipsum import register_lorem_ipsum_skill
    from .skillify import register_skillify_skill
    from .remember import register_remember_skill
    from .simplify import register_simplify_skill
    from .batch import register_batch_skill
    from .stuck import register_stuck_skill

    register_update_config_skill()
    register_keybindings_skill()
    register_verify_skill()
    register_debug_skill()
    register_lorem_ipsum_skill()
    register_skillify_skill()
    register_remember_skill()
    register_simplify_skill()
    register_batch_skill()
    register_stuck_skill()

    # Feature-gated skills
    if _feature("loop") or _feature("agent_triggers"):
        from .loop import register_loop_skill
        register_loop_skill()

    if _feature("schedule_remote_agents") or _feature("agent_triggers_remote"):
        from .schedule_remote_agents import register_schedule_remote_agents_skill
        register_schedule_remote_agents_skill()

    if _feature("vivian_api"):
        from .vivian_api import register_vivian_api_skill
        register_vivian_api_skill()

    if _feature("vivian_in_chrome"):
        from .vivian_in_chrome import register_vivian_in_chrome_skill
        register_vivian_in_chrome_skill()

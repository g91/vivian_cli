"""UpdateConfig skill — mirrors src/skills/bundled/updateConfig.ts."""
from __future__ import annotations

from typing import Any

from ..bundled_skills import BundledSkillDefinition, register_bundled_skill

_SETTINGS_DOCS = """## Settings File Locations

Choose the appropriate file based on scope:

| File | Scope | Git | Use For |
|------|-------|-----|---------|
| `~/.vivian/settings.json` | Global | N/A | Personal preferences for all projects |
| `.vivian/settings.json` | Project | Commit | Team-wide hooks, permissions, plugins |
| `.vivian/settings.local.json` | Project | Gitignore | Personal overrides for this project |

Settings load in order: user → project → local (later overrides earlier).
"""

_UPDATE_CONFIG_PROMPT = f"""# UpdateConfig: Modify vivian Code Settings

Help the user view or update vivian Code configuration.

{_SETTINGS_DOCS}

## Your Task

1. Ask the user what they want to configure (or read their request from args).
2. Determine the appropriate settings file based on scope.
3. Read the current settings if the file exists.
4. Apply the requested changes using the Edit or Write tool.
5. Confirm what was changed.

## Common Settings

- `model`: AI model to use (e.g., `vivian-opus-4-5`)
- `hooks`: Pre/post tool execution hooks
- `permissions`: Tool permission overrides
- `env`: Environment variable overrides
"""


def register_update_config_skill() -> None:
    register_bundled_skill(BundledSkillDefinition(
        name="updateConfig",
        description="Update vivian Code settings (model, hooks, permissions, etc.).",
        user_invocable=True,
        get_prompt_for_command=lambda args="", ctx=None: [
            {"type": "text", "text": _UPDATE_CONFIG_PROMPT}
        ],
    ))

"""Load skills from a directory — mirrors src/skills/loadSkillsDir.ts."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .bundled_skills import BundledSkillDefinition, register_bundled_skill


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("---", 3)
    if end == -1:
        return {}, text
    block = text[3:end]
    body = text[end + 3:].lstrip("\n")
    fm: dict = {}
    for line in block.splitlines():
        m = re.match(r"^([\w-]+)\s*:\s*(.+)$", line.strip())
        if m:
            fm[m.group(1).strip()] = m.group(2).strip()
    return fm, body


def load_skills_dir(directory: str | Path) -> list[BundledSkillDefinition]:
    """Load .md skill files from *directory* as skill definitions.

    Scans both top-level *.md files AND */SKILL.md in subdirectories
    so that skills organised in folders (e.g. my-skill/SKILL.md) are found.
    """
    path = Path(directory)
    if not path.is_dir():
        return []
    skills: list[BundledSkillDefinition] = []
    # Top-level .md files (legacy flat layout)
    candidates = sorted(path.glob("*.md"))
    # Subdirectory SKILL.md files (standard layout: <skill-name>/SKILL.md)
    candidates += sorted(path.glob("*/SKILL.md"))
    for md in candidates:
        try:
            text = md.read_text(errors="replace")
            fm, body = _parse_frontmatter(text)
            name = str(fm.get("name", md.stem))
            description = str(fm.get("description", f"Custom skill: {name}"))
            allowed_raw = fm.get("allowed-tools", fm.get("allowedTools"))
            allowed_tools = [t.strip() for t in allowed_raw.split(",")] if allowed_raw else None
            model = fm.get("model") or None
            prompt_body = body.strip()
            skill = BundledSkillDefinition(
                name=name,
                description=description,
                get_prompt_for_command=lambda args="", ctx=None, _prompt_body=prompt_body: _prompt_body,
                allowed_tools=allowed_tools,
                model=model,
                when_to_use=str(fm.get("when-to-use", fm.get("whenToUse", ""))) or None,
                argument_hint=str(fm.get("argument-hint", fm.get("argumentHint", ""))) or None,
            )
            skills.append(skill)
        except OSError:
            continue
    return skills

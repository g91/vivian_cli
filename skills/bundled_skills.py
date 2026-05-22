"""Bundled skills registry — mirrors src/skills/bundledSkills.ts.

Programmatic skill registration for skills that ship with the CLI.
"""
from __future__ import annotations

import logging
import os
import stat
from dataclasses import dataclass, field
from os.path import dirname, isabs, join, normpath
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)


@dataclass
class BundledSkillDefinition:
    """Definition for a bundled skill that ships with the CLI."""
    name: str
    description: str
    get_prompt_for_command: Callable[..., Any]
    aliases: Optional[list[str]] = None
    when_to_use: Optional[str] = None
    argument_hint: Optional[str] = None
    allowed_tools: Optional[list[str]] = None
    model: Optional[str] = None
    disable_model_invocation: bool = False
    user_invocable: bool = True
    is_enabled: Optional[Callable[[], bool]] = None
    hooks: Optional[Any] = None
    context: Optional[str] = None  # 'inline' | 'fork'
    agent: Optional[str] = None
    files: Optional[dict[str, str]] = None


# Internal registry
_bundled_skills: list[dict] = []


def register_bundled_skill(definition: BundledSkillDefinition) -> None:
    """Register a bundled skill into the global registry."""
    files = definition.files
    skill_root: Optional[str] = None
    get_prompt = definition.get_prompt_for_command

    if files and files:
        skill_root = get_bundled_skill_extract_dir(definition.name)
        _extraction_cache: dict[str, Optional[str]] = {}
        inner_get_prompt = definition.get_prompt_for_command

        def _wrapped_get_prompt(args, ctx):
            key = definition.name
            if key not in _extraction_cache:
                try:
                    _write_skill_files(skill_root, files)
                    _extraction_cache[key] = skill_root
                except Exception as e:
                    log.debug(
                        "Failed to extract bundled skill '%s' to %s: %s",
                        definition.name,
                        skill_root,
                        e,
                    )
                    _extraction_cache[key] = None

            extracted_dir = _extraction_cache.get(key)
            blocks = inner_get_prompt(args, ctx)
            if extracted_dir is None:
                return blocks
            return _prepend_base_dir(blocks, extracted_dir)

        get_prompt = _wrapped_get_prompt

    command = {
        "type": "prompt",
        "name": definition.name,
        "description": definition.description,
        "aliases": definition.aliases,
        "has_user_specified_description": True,
        "allowed_tools": definition.allowed_tools or [],
        "argument_hint": definition.argument_hint,
        "when_to_use": definition.when_to_use,
        "model": definition.model,
        "disable_model_invocation": definition.disable_model_invocation,
        "user_invocable": definition.user_invocable,
        "content_length": 0,
        "source": "bundled",
        "loaded_from": "bundled",
        "hooks": definition.hooks,
        "skill_root": skill_root,
        "context": definition.context,
        "agent": definition.agent,
        "is_enabled": definition.is_enabled,
        "is_hidden": not definition.user_invocable,
        "progress_message": "running",
        "get_prompt_for_command": get_prompt,
    }
    _bundled_skills.append(command)


def get_bundled_skills() -> list[dict]:
    """Return a copy of all registered bundled skills."""
    return list(_bundled_skills)


def get_bundled_skill(name: str) -> Optional[dict]:
    """Return the registered bundled skill with the given name, or None."""
    for skill in _bundled_skills:
        if skill.get("name") == name:
            return skill
    return None


def clear_bundled_skills() -> None:
    """Clear the bundled skills registry (for testing)."""
    _bundled_skills.clear()


def get_bundled_skill_extract_dir(skill_name: str) -> str:
    """Return the extraction directory for a bundled skill's reference files."""
    from ..utils.permissions.filesystem import get_bundled_skills_root
    return join(get_bundled_skills_root(), skill_name)


def _write_skill_files(base_dir: str, files: dict[str, str]) -> None:
    """Write bundled skill reference files to disk."""
    os.makedirs(base_dir, mode=0o700, exist_ok=True)
    for rel_path, content in files.items():
        target = _resolve_skill_file_path(base_dir, rel_path)
        parent = dirname(target)
        os.makedirs(parent, mode=0o700, exist_ok=True)
        _safe_write_file(target, content)


def _safe_write_file(path: str, content: str) -> None:
    """Write a file with O_EXCL | O_NOFOLLOW semantics where available."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        return  # Already extracted
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
    except Exception:
        try:
            os.close(fd)
        except Exception:
            pass
        raise


def _resolve_skill_file_path(base_dir: str, rel_path: str) -> str:
    """Validate and resolve a skill-relative path; raises on traversal."""
    normalized = normpath(rel_path)
    if isabs(normalized):
        raise ValueError(f"bundled skill file path is absolute: {rel_path}")
    parts = normalized.replace("\\", "/").split("/")
    if ".." in parts:
        raise ValueError(f"bundled skill file path escapes skill dir: {rel_path}")
    return join(base_dir, normalized)


def _prepend_base_dir(blocks: list, base_dir: str) -> list:
    """Prepend a base-directory header to the first text block."""
    prefix = f"Base directory for this skill: {base_dir}\n\n"
    if blocks and isinstance(blocks[0], dict) and blocks[0].get("type") == "text":
        return [{"type": "text", "text": prefix + blocks[0]["text"]}, *blocks[1:]]
    return [{"type": "text", "text": prefix}, *blocks]

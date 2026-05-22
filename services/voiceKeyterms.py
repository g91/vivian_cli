"""Voice keyterms — mirrors src/services/voiceKeyterms.ts."""
from __future__ import annotations

import asyncio
import os
import re
from typing import Optional

GLOBAL_KEYTERMS: tuple[str, ...] = (
    "MCP",
    "symlink",
    "grep",
    "regex",
    "localhost",
    "codebase",
    "TypeScript",
    "JSON",
    "OAuth",
    "webhook",
    "gRPC",
    "dotfiles",
    "subagent",
    "worktree",
)

MAX_KEYTERMS = 50


def splitIdentifier(name: str) -> list[str]:
    """Split an identifier (camelCase, PascalCase, kebab-case, snake_case) into words.

    Mirrors splitIdentifier() from voiceKeyterms.ts.
    """
    expanded = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    parts = re.split(r"[-_./\s]+", expanded)
    return [w.strip() for w in parts if 2 < len(w.strip()) <= 20]


def _file_name_words(file_path: str) -> list[str]:
    stem = os.path.splitext(os.path.basename(file_path))[0]
    return splitIdentifier(stem)


async def getVoiceKeyterms(recent_files: Optional[set] = None) -> list[str]:
    """Build a list of keyterms for the voice_stream STT endpoint.

    Mirrors getVoiceKeyterms() from voiceKeyterms.ts.
    """
    terms: set[str] = set(GLOBAL_KEYTERMS)

    try:
        from ..bootstrap.state import get_project_root
        project_root = get_project_root()
        if project_root:
            name = os.path.basename(project_root)
            if 2 < len(name) <= 50:
                terms.add(name)
    except Exception:
        pass

    try:
        from ..utils.git import get_branch
        branch = await get_branch() if asyncio.iscoroutinefunction(get_branch) else get_branch()  # type: ignore
        if branch:
            for word in splitIdentifier(branch):
                terms.add(word)
    except Exception:
        pass

    if recent_files:
        for file_path in recent_files:
            if len(terms) >= MAX_KEYTERMS:
                break
            for word in _file_name_words(file_path):
                terms.add(word)

    return list(terms)[:MAX_KEYTERMS]


split_identifier = splitIdentifier
get_voice_keyterms = getVoiceKeyterms

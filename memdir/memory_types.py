"""Memory system types and constants — mirrors src/memdir/memoryTypes.ts."""
from __future__ import annotations

from typing import Literal, Optional

MEMORY_TYPES = ("user", "feedback", "project", "reference")
MemoryType = Literal["user", "feedback", "project", "reference"]


def parse_memory_type(raw: str) -> Optional[str]:
    if raw in MEMORY_TYPES:
        return raw
    return None


TYPES_SECTION_INDIVIDUAL = """\
## Memory type: {type}

{description}"""

TYPES_SECTION_COMBINED = """\
Memory types:
- **user** — personal preferences and patterns for this user
- **feedback** — corrections and feedback given by the user  
- **project** — project-specific context, conventions, and notes
- **reference** — factual reference material, API docs, snippets"""

MEMORY_FRONTMATTER_EXAMPLE = """\
---
type: user
description: Brief one-line description of what this memory contains
---"""

WHEN_TO_ACCESS_SECTION = """\
## When to access memories

Load memories when the user's request involves:
- Their personal preferences or past feedback
- Project-specific context that's been stored
- Reference material related to the current task

Do not load memories for trivial requests or when you already have full context."""

WHAT_NOT_TO_SAVE_SECTION = """\
## What not to save

Do not save:
- Sensitive data (passwords, tokens, keys)
- Transient runtime values
- Content that belongs in source control
- Information the user explicitly said not to save"""

TRUSTING_RECALL_SECTION = """\
## Trusting recalled memories

Treat recalled memories as plausible context, not ground truth.
The user may have changed their mind since a memory was written.
If a recalled memory contradicts what the user just said, defer to what they said."""

MEMORY_DRIFT_CAVEAT = (
    "- **Memory drift**: memories can go stale. Before answering based on a memory, "
    "verify it against the current project state (read the relevant files, check "
    "git log). If the memory contradicts current reality, trust the code and "
    "update or remove the stale memory."
)

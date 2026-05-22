"""MagicDocs service — mirrors src/services/MagicDocs/magicDocs.ts."""
from __future__ import annotations

MAGIC_DOC_HEADER_PATTERN = r"^#\s*MAGIC\s+DOC:\s*(.+)$"


def isMagicDoc(content: str) -> bool:
    """Check if file content is a magic doc."""
    import re
    return bool(re.search(MAGIC_DOC_HEADER_PATTERN, content, re.MULTILINE | re.IGNORECASE))


is_magic_doc = isMagicDoc

"""Display tag stripping — mirrors src/utils/displayTags.ts"""
from __future__ import annotations

import re

_XML_TAG_BLOCK_PATTERN = re.compile(
    r"<([a-z][\w-]*)(?:\s[^>]*)?>[\s\S]*?</\1>\n?", re.MULTILINE
)

_IDE_CONTEXT_TAGS_PATTERN = re.compile(
    r"<(ide_opened_file|ide_selection)(?:\s[^>]*)?>[\s\S]*?</\1>\n?", re.MULTILINE
)


def strip_display_tags(text: str) -> str:
    """Strip XML-like system tag blocks from text for use in UI titles.

    If stripping would result in empty text, returns the original unchanged.
    """
    result = _XML_TAG_BLOCK_PATTERN.sub("", text).strip()
    return result or text


def strip_display_tags_allow_empty(text: str) -> str:
    """Like strip_display_tags but returns empty string if all content is tags."""
    return _XML_TAG_BLOCK_PATTERN.sub("", text).strip()


def strip_ide_context_tags(text: str) -> str:
    """Strip only IDE-injected context tags (ide_opened_file, ide_selection)."""
    return _IDE_CONTEXT_TAGS_PATTERN.sub("", text).strip()

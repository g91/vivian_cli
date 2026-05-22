"""
Port of src/utils/pdfUtils.ts
"""
from __future__ import annotations

from typing import Any

from .model.model import getMainLoopModel


DOCUMENT_EXTENSIONS: Any = {'pdf'}


def parsePDFPageRange(pages):
    """Parse a page range string into firstPage/lastPage numbers.
Supported formats:
- "5" → { firstPage: 5, lastPage: 5 }
- "1-10" → { firstPage: 1, lastPage: 10 }
- "3-" → { firstPage: 3, lastPage: Infinity }

Returns null on invalid input (non-numeric, zero, inverted range).
Pages are 1-indexed."""
    trimmed = str(pages).strip() if pages is not None else ""
    if not trimmed:
        return None

    if trimmed.endswith('-'):
        try:
            first = int(trimmed[:-1])
        except ValueError:
            return None
        if first < 1:
            return None
        return {'firstPage': first, 'lastPage': float('inf')}

    dash_index = trimmed.find('-')
    if dash_index == -1:
        try:
            page = int(trimmed)
        except ValueError:
            return None
        if page < 1:
            return None
        return {'firstPage': page, 'lastPage': page}

    try:
        first = int(trimmed[:dash_index])
        last = int(trimmed[dash_index + 1:])
    except ValueError:
        return None
    if first < 1 or last < 1 or last < first:
        return None
    return {'firstPage': first, 'lastPage': last}


def isPDFSupported():
    """Check if PDF reading is supported with the current model.
PDF document blocks work on all providers (1P, Vertex, Bedrock, Foundry).
Haiku 3 is the only remaining model that predates PDF support; users on
it fall back to the page-extraction path (poppler-utils). Substring match
covers all provider ID formats (Bedrock prefixes, Vertex @-dates)."""
    return 'vivian-3-haiku' not in getMainLoopModel().lower()


def isPDFExtension(ext):
    """Check if a file extension is a PDF document.
@param ext File extension (with or without leading dot)"""
    normalized = str(ext or '')
    if normalized.startswith('.'):
        normalized = normalized[1:]
    return normalized.lower() in DOCUMENT_EXTENSIONS


parse_pdf_page_range = parsePDFPageRange
is_pdf_supported = isPDFSupported
is_pdf_extension = isPDFExtension


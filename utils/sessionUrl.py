"""
Port of src/utils/sessionUrl.ts
"""
from __future__ import annotations

from typing import Any, Dict
import uuid
from urllib.parse import urlparse

from .uuid import validate_uuid


ParsedSessionUrl = Dict[str, Any]


def parseSessionIdentifier(resumeIdentifier: str) -> ParsedSessionUrl | None:
    """Parses a session resume identifier which can be either:
- A URL containing session ID (e.g., https://api.example.com/v1/session_ingress/session/550e8400-e29b-41d4-a716-446655440000)
- A plain session ID (UUID)

@param resumeIdentifier - The URL or session ID to parse
@returns Parsed session information or null if invalid"""
    if not isinstance(resumeIdentifier, str):
        return None

    if resumeIdentifier.lower().endswith('.jsonl'):
        return {
            'sessionId': str(uuid.uuid4()),
            'ingressUrl': None,
            'isUrl': False,
            'jsonlFile': resumeIdentifier,
            'isJsonlFile': True,
        }

    validated_uuid = validate_uuid(resumeIdentifier)
    if validated_uuid:
        return {
            'sessionId': validated_uuid,
            'ingressUrl': None,
            'isUrl': False,
            'jsonlFile': None,
            'isJsonlFile': False,
        }

    try:
        parsed = urlparse(resumeIdentifier)
        if parsed.scheme and parsed.netloc:
            return {
                'sessionId': str(uuid.uuid4()),
                'ingressUrl': parsed.geturl(),
                'isUrl': True,
                'jsonlFile': None,
                'isJsonlFile': False,
            }
    except Exception:
        pass

    return None


parse_session_identifier = parseSessionIdentifier


"""
Port of src/utils/fingerprint.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import hashlib

from ..constants import PRODUCT_VERSION


# Hardcoded salt from backend validation.
FINGERPRINT_SALT: Any = '59cf53e54c78'  # type: ignore


def extractFirstMessageText(messages):
    """Extracts text content from the first user message."""
    for message in messages or []:
        if not isinstance(message, dict) or message.get('type') != 'user':
            continue
        payload = message.get('message') if isinstance(message.get('message'), dict) else message
        content = payload.get('content') if isinstance(payload, dict) else None
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get('type') == 'text' and isinstance(block.get('text'), str):
                    return block['text']
        return ''
    return ''


def computeFingerprint(messageText, version):
    """Computes 3-character fingerprint for vivian Code attribution."""
    text = '' if messageText is None else str(messageText)
    version_text = '' if version is None else str(version)
    chars = ''.join(text[index] if index < len(text) else '0' for index in (4, 7, 20))
    fingerprint_input = f'{FINGERPRINT_SALT}{chars}{version_text}'
    return hashlib.sha256(fingerprint_input.encode('utf-8')).hexdigest()[:3]


def computeFingerprintFromMessages(messages):
    """Computes fingerprint from the first user message."""
    first_message_text = extractFirstMessageText(messages)
    return computeFingerprint(first_message_text, PRODUCT_VERSION)


extract_first_message_text = extractFirstMessageText
compute_fingerprint = computeFingerprint
compute_fingerprint_from_messages = computeFingerprintFromMessages


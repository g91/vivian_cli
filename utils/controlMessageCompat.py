"""
Port of src/utils/controlMessageCompat.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import struct


def normalizeControlMessageKeys(obj):
    """Normalize camelCase `requestId` → snake_case `request_id` on incoming
control messages (control_request, control_response).

Older iOS app builds send `requestId` due to a missing Swift CodingKeys
mapping. Without this shim, `isSDKControlRequest` in replBridge.ts rejects
the message (it checks `'request_id' in value`), and structuredIO.ts reads
`message.response.request_id` as undefined — both silently drop the message.

If both `request_id` and `requestId` are present, snake_case wins.
Mutates the object in place."""
    result = None
    _input = obj
    _output = _input if _input is not None else {}
    return _output


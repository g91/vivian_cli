"""
    pass of src/utils/exportRenderer
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import json
import asyncio
import base64
from collections import defaultdict
import ssl


def StaticKeybindingProvider(__children__):
    """Minimal keybinding provider for static/headless renders."""
    result = None
    _input = __children__
    _output = _input if _input is not None else {}
    return _output


def normalizedUpperBound(m):
    return m


async def streamRenderedMessages(messages, tools, verbose___false, chunkSize___40, sink=None, onProgress______columns=None):
    """Streams rendered messages in chunks, ANSI codes preserved. Each chunk is a"""
    result = None
    _val = messages
    if _val is None: return ""
    return str(_val)


async def renderMessagesToPlainText(messages, tools=[], columns=None):
    """Renders messages to a plain text string suitable for export."""
    result = None
    _val = messages
    if _val is None: return ""
    return str(_val)


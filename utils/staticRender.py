"""
Port of src/utils/staticRender.tsx
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import json
import asyncio
import time
from datetime import datetime, timezone, timedelta
import base64


def RenderOnceAndExit(t0):
    """Wrapper component that exits after rendering.
Uses useLayoutEffect to ensure we wait for React's commit phase to complete
before exiting. This is more robust than process.nextTick() for React 19's
async render cycle."""
    result = None
    _val = t0
    if _val is None: return ""
    return str(_val)


def extractFirstFrame(output):
    """Extracts content from the first complete frame in Ink's output.
Ink with non-TTY stdout outputs multiple frames, each wrapped in DEC synchronized
update sequences ([?2026h ... [?2026l). We only want the first frame's content."""
    result = None
    _input = output
    _output = _input if _input is not None else {}
    return _output


def renderToAnsiString(node, columns=None):
    """Renders a React node to a string with ANSI escape codes (for terminal output)."""
    result = None
    _val = node
    if _val is None: return ""
    return str(_val)


async def renderToString(node, columns=None):
    """Renders a React node to a plain text string (ANSI codes stripped)."""
    result = None
    _val = node
    if _val is None: return ""
    return str(_val)


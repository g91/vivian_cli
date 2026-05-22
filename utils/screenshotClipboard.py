"""
Port of src/utils/screenshotClipboard.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import re
import asyncio
import time
from datetime import datetime, timezone, timedelta
import platform


async def copyAnsiToClipboard(ansiText, options=None):
    """Copies an image (from ANSI text) to the system clipboard.
Supports macOS, Linux (with xclip/xsel), and Windows.

Pure-TS pipeline: ANSI text → bitmap-font render → PNG encode. No WASM,
no system fonts, so this works in every build (native and JS)."""
    success; message


async def copyPngToClipboard(pngPath):
    success: boolean; message


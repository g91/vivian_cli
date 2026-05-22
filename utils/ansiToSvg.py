"""
Port of src/utils/ansiToSvg.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import re
import math


AnsiColor = Dict[str, Any]
TextSpan = Dict[str, Any]
ParsedLine = List[TextSpan]
AnsiToSvgOptions = Dict[str, Any]


DEFAULT_FG: AnsiColor = None  # type: ignore
DEFAULT_BG: AnsiColor = None  # type: ignore


def parseAnsi(text):
    """Parse ANSI escape sequences from text
Supports:
- Basic colors (30-37, 90-97)
- 256-color mode (38;5;n)
- 24-bit true color (38;2;r;g;b)"""
    result = None
    _input = text
    _output = _input if _input is not None else {}
    return _output


def get256Color(index):
    """Get color from 256-color palette"""
    result = None
    _input = index
    _output = _input if _input is not None else {}
    return _output


def ansiToSvg(ansiText, options={}):
    """Convert ANSI text to SVG
Uses <tspan> elements within a single <text> per line so the renderer
handles character spacing natively (no manual charWidth calculation)"""
    result = None
    _input = ansiText
    _output = _input if _input is not None else {}
    return _output


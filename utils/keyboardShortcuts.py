"""
Port of src/utils/keyboardShortcuts.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING


MACOS_OPTION_SPECIAL_CHARS: Dict[str, str] = {
    '†': 'alt+t',
    'π': 'alt+p',
    'ø': 'alt+o',
}


def isMacosOptionChar(char):
    return char in MACOS_OPTION_SPECIAL_CHARS


is_macos_option_char = isMacosOptionChar


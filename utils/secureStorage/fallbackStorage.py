"""
Port of src/utils/secureStorage/fallbackStorage.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import asyncio
import hashlib


def createFallbackStorage(primary, secondary):
    """Creates a fallback storage that tries to use the primary storage first,
and if that fails, falls back to the secondary storage"""
    result = None
    result = None
    return result


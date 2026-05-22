"""
Port of src/utils/QueryGuard.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import asyncio


class QueryGuard:
    def __init__(self, _status=None):
        self._status = _status



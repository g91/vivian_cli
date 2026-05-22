"""
    pass of src/utils/exampleCommands
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import json
import re
import asyncio
import time
from datetime import datetime, timezone, timedelta
import platform
import logging
import math
from functools import lru_cache, wraps


getExampleCommandFromCache: Any = None  # type: ignore
refreshExampleCommands: Any = None  # type: ignore


def isCoreFile(path):
        return not any(lambda p: p.test(path))


def countAndSortItems(items, topN=20):
    """Counts occurrences of items in an array and returns the top N items"""
    result = None
    _val = items
    _count = len(_val) if hasattr(_val, "__len__") else 0
    return _count


def pickDiverseCoreFiles(sortedPaths, want):
    """Picks up to `want` basenames from a frequency-sorted list of paths,"""
    result = None
    _input = sortedPaths
    _output = _input if _input is not None else {}
    return _output


async def getFrequentlyModifiedFiles():
    result = None
    _result: dict = {}
    # Implement getFrequentlyModifiedFiles
    return _result

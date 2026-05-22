"""
Port of src/utils/toolSchemaCache.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING


CachedSchema = Any


def getToolSchemaCache():
    return TOOL_SCHEMA_CACHE


def clearToolSchemaCache():
    TOOL_SCHEMA_CACHE.clear()


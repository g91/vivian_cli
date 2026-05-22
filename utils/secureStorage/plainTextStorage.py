"""
Port of src/utils/secureStorage/plainTextStorage.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import json
import asyncio


plainTextStorage: Any = None  # type: ignore


def getStoragePath():
    storageDir: string; storagePath


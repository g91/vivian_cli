"""
Port of src/utils/glob.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import re
import asyncio
import glob
import platform
import math


def extractGlobBaseDirectory(pattern):
    """Extracts the static base directory from a glob pattern.
The base directory is everything before the first glob special character (* ? [ {).
Returns the directory portion and the remaining relative pattern."""
    baseDir
    relativePattern


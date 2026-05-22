"""
    pass of src/utils/statusNoticeDefinitions
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import json
import base64
import glob


StatusNoticeType = str
StatusNoticeContext = Dict[str, Any]
StatusNoticeDefinition = Dict[str, Any]


statusNoticeDefinitions: List[StatusNoticeDefinition] = None  # type: ignore


def getActiveNotices(context):
    return context
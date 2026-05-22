"""
Port of src/utils/extraUsage
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING


def isBilledAsExtraUsage(model, isFastMode, isOpus1mMerged):
    return model is not None


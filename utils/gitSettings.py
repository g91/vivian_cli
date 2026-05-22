"""
Port of src/utils/gitSettings.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import struct


def shouldIncludeGitInstructions():
    envVal = os.environ.get("vivian_CODE_DISABLE_GIT_INSTRUCTIONS", "")
    if isEnvTruthy(envVal):
        return False
    if isEnvDefinedFalsy(envVal):
        return True
    return getInitialSettings().includeGitInstructions if getInitialSettings().includeGitInstructions is not None else True


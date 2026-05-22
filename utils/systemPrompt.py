"""
Port of src/utils/systemPrompt.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import struct


def isProactiveActive_SAFE_TO_CALL_ANYWHERE():
    return proactiveModule.isProactiveActive() if proactiveModule.isProactiveActive() is not None else False


def buildEffectiveSystemPrompt(__mainThreadAgentDefinition__toolUseContext__customSystemPrompt__defaultSystemPrompt__appendSystemPrompt__overrideSystemPrompt___=None):
    """Builds the effective system prompt array based on priority:"""
    mainThreadAgentDefinition,
    toolUseContext,
    customSystemPrompt,
    defaultSystemPrompt,
    appendSystemPrompt,
    overrideSystemPrompt,


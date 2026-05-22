"""Port of src/utils/model/aliases.ts"""
from __future__ import annotations

from typing import Literal

MODEL_ALIASES = (
    'sonnet',
    'opus',
    'haiku',
    'best',
    'sonnet[1m]',
    'opus[1m]',
    'opusplan',
)

ModelAlias = Literal['sonnet', 'opus', 'haiku', 'best', 'sonnet[1m]', 'opus[1m]', 'opusplan']

def isModelAlias(modelInput: str) -> bool:
    return modelInput in MODEL_ALIASES

# Bare model family aliases that act as wildcards in the availableModels allowlist.
MODEL_FAMILY_ALIASES = ('sonnet', 'opus', 'haiku')

def isModelFamilyAlias(model: str) -> bool:
    return model in MODEL_FAMILY_ALIASES

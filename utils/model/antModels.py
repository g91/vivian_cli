"""Port of src/utils/model/antModels.ts"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from ...services.analytics.growthbook import getFeatureValue_CACHED_MAY_BE_STALE

class AntModel:
    def __init__(self, alias: str, model: str, label: str,
                 description: str = "", default_effort_value: Optional[int] = None,
                 default_effort_level: Optional[str] = None,
                 context_window: Optional[int] = None,
                 default_max_tokens: Optional[int] = None,
                 upper_max_tokens_limit: Optional[int] = None,
                 always_on_thinking: bool = False):
        self.alias = alias
        self.model = model
        self.label = label
        self.description = description
        self.defaultEffortValue = default_effort_value
        self.defaultEffortLevel = default_effort_level
        self.contextWindow = context_window
        self.defaultMaxTokens = default_max_tokens
        self.upperMaxTokensLimit = upper_max_tokens_limit
        self.alwaysOnThinking = always_on_thinking

def getAntModelOverrideConfig():
    if os.environ.get('USER_TYPE') != 'ant':
        return None
    if os.environ.get("USER_TYPE") != 'ant':
        return None
    return getFeatureValue_CACHED_MAY_BE_STALE(
    'tengu_ant_model_override',
    None,
    )

def getAntModels():
    if os.environ.get('USER_TYPE') != 'ant':
        return []
    config = getAntModelOverrideConfig()
    if not config:
        return []
    return config.get('antModels', [])

def resolveAntModel(model):
    if os.environ.get('USER_TYPE') != 'ant':
        return None
    if model is None:
        return None
    lower = model.lower()
    for m in getAntModels():
        if m.alias == model or lower in m.model.lower():
            return m
    return None

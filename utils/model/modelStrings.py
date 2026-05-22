"""Port of src/utils/model/modelStrings.ts"""
from __future__ import annotations

import os
from typing import Dict, Optional

from .configs import ALL_MODEL_CONFIGS, CANONICAL_ID_TO_KEY, ModelConfig
from .providers import getAPIProvider

ModelStrings = Dict[str, str]  # ModelKey -> model string

_model_strings_state: Optional[ModelStrings] = None

def _get_builtin_model_strings(provider: str) -> ModelStrings:
    out: ModelStrings = {}
    for key, cfg in ALL_MODEL_CONFIGS.items():
        out[key] = cfg.get(provider, cfg['firstParty'])
    return out

def _apply_model_overrides(ms: ModelStrings) -> ModelStrings:
    try:
        from ..settings.settings import getInitialSettings
        overrides = getInitialSettings().get('modelOverrides')
    except Exception:
        return ms
    if not overrides:
        return ms
    out = dict(ms)
    for canonical_id, override in overrides.items():
        key = CANONICAL_ID_TO_KEY.get(canonical_id)
        if key and override:
            out[key] = override
    return out

def resolveOverriddenModel(model_id: str) -> str:
    try:
        from ..settings.settings import getInitialSettings
        overrides = getInitialSettings().get('modelOverrides') or {}
    except Exception:
        return model_id
    for canonical_id, override in overrides.items():
        if override == model_id:
            return canonical_id
    return model_id

def getModelStrings() -> ModelStrings:
    global _model_strings_state
    if _model_strings_state is None:
        provider = getAPIProvider()
        _model_strings_state = _get_builtin_model_strings(provider)
    return _apply_model_overrides(_model_strings_state)

def setModelStrings(ms: ModelStrings) -> None:
    global _model_strings_state
    _model_strings_state = ms

async def ensureModelStringsInitialized() -> None:
    global _model_strings_state
    if _model_strings_state is not None:
        return
    provider = getAPIProvider()
    _model_strings_state = _get_builtin_model_strings(provider)

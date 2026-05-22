"""Port of src/utils/model/modelCapabilities.ts"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from .providers import getAPIProvider, isFirstPartyAnthropicBaseUrl


def _get_cache_dir():
    try:
        from ..envUtils import getvivianConfigHomeDir
        return os.path.join(getvivianConfigHomeDir(), 'cache')
    except Exception:
        return os.path.expanduser('~/.vivian/cache')


def _get_cache_path():
    return os.path.join(_get_cache_dir(), 'model-capabilities.json')


def _is_eligible():
    if os.environ.get('USER_TYPE') != 'ant':
        return False
    if getAPIProvider() != 'firstParty':
        return False
    if not isFirstPartyAnthropicBaseUrl():
        return False
    return True


_cached_capabilities = None

ModelCapability = Dict[str, Any]


def _load_cache():
    global _cached_capabilities
    if _cached_capabilities is not None:
        return _cached_capabilities
    try:
        path = _get_cache_path()
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        models = data.get('models', [])
        _cached_capabilities = models
        return models
    except Exception:
        return None


def getModelCapability(model):
    if not _is_eligible():
        return None
    cached = _load_cache()
    if not cached:
        return None
    m = model.lower()
    for c in cached:
        if c.get('id', '').lower() == m:
            return c
    for c in cached:
        if m in c.get('id', '').lower():
            return c
    return None


async def refreshModelCapabilities():
    if not _is_eligible():
        return
    try:
        from ..privacyLevel import isEssentialTrafficOnly
        if isEssentialTrafficOnly():
            return
    except Exception:
        pass

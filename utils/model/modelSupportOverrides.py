"""Port of src/utils/model/modelSupportOverrides.ts"""
from __future__ import annotations

import os
from typing import Optional

ModelCapabilityOverride = str  # 'effort'|'max_effort'|'thinking'|...

TIERS = [
    {
        'modelEnvVar': 'ANTHROPIC_DEFAULT_OPUS_MODEL',
        'capabilitiesEnvVar': 'ANTHROPIC_DEFAULT_OPUS_MODEL_SUPPORTED_CAPABILITIES',
    },
    {
        'modelEnvVar': 'ANTHROPIC_DEFAULT_SONNET_MODEL',
        'capabilitiesEnvVar': 'ANTHROPIC_DEFAULT_SONNET_MODEL_SUPPORTED_CAPABILITIES',
    },
    {
        'modelEnvVar': 'ANTHROPIC_DEFAULT_HAIKU_MODEL',
        'capabilitiesEnvVar': 'ANTHROPIC_DEFAULT_HAIKU_MODEL_SUPPORTED_CAPABILITIES',
    },
]


def get3PModelCapabilityOverride(model, capability):
    from .providers import getAPIProvider
    if getAPIProvider() == 'firstParty':
        return None
    m = model.lower()
    for tier in TIERS:
        pinned = os.environ.get(tier['modelEnvVar'])
        capabilities = os.environ.get(tier['capabilitiesEnvVar'])
        if not pinned or capabilities is None:
            continue
        if m != pinned.lower():
            continue
        caps = [s.strip() for s in capabilities.lower().split(',')]
        return capability in caps
    return None

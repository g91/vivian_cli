"""Port of src/utils/model/deprecation.ts"""
from __future__ import annotations

from typing import Dict, Optional

# Deprecated models and their retirement dates by provider.
# Keys are substrings to match in model IDs (case-insensitive).
DEPRECATED_MODELS: Dict[str, Dict] = {
    'vivian-3-opus': {
        'modelName': 'vivian 3 Opus',
        'retirementDates': {
            'firstParty': 'January 5, 2026',
            'bedrock': 'January 15, 2026',
            'vertex': 'January 5, 2026',
            'foundry': 'January 5, 2026',
        },
    },
    'vivian-3-7-sonnet': {
        'modelName': 'vivian 3.7 Sonnet',
        'retirementDates': {
            'firstParty': 'February 19, 2026',
            'bedrock': 'April 28, 2026',
            'vertex': 'May 11, 2026',
            'foundry': 'February 19, 2026',
        },
    },
    'vivian-3-5-haiku': {
        'modelName': 'vivian 3.5 Haiku',
        'retirementDates': {
            'firstParty': 'February 19, 2026',
            'bedrock': None,
            'vertex': None,
            'foundry': None,
        },
    },
}

def _get_deprecated_model_info(model_id: str) -> Optional[Dict]:
    from .providers import getAPIProvider
    provider = getAPIProvider()
    lower = model_id.lower()
    for key, value in DEPRECATED_MODELS.items():
        retirement_date = value['retirementDates'].get(provider)
        if key not in lower or not retirement_date:
            continue
        return {
            'isDeprecated': True,
            'modelName': value['modelName'],
            'retirementDate': retirement_date,
        }
    return {'isDeprecated': False}

def getModelDeprecationWarning(model_id: Optional[str]) -> Optional[str]:
    if not model_id:
        return None
    info = _get_deprecated_model_info(model_id)
    if not info or not info.get('isDeprecated'):
        return None
    return (
        f"⚠ {info['modelName']} will be retired on {info['retirementDate']}. "
        "Consider switching to a newer model."
    )

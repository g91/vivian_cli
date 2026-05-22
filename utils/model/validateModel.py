"""Port of src/utils/model/validateModel.ts"""
from __future__ import annotations

import os
from typing import Dict, Optional, Tuple

from .aliases import MODEL_ALIASES
from .modelAllowlist import isModelAllowed

_valid_model_cache: Dict[str, bool] = {}

async def validateModel(model: str) -> Dict:
    normalized = model.strip()
    if not normalized:
        return {'valid': False, 'error': 'Model name cannot be empty'}

    if not isModelAllowed(normalized):
        return {
            'valid': False,
            'error': f"Model '{normalized}' is not in the list of available models",
        }

    if normalized.lower() in [a.lower() for a in MODEL_ALIASES]:
        return {'valid': True}

    if normalized == os.environ.get('ANTHROPIC_CUSTOM_MODEL_OPTION'):
        return {'valid': True}

    if normalized in _valid_model_cache:
        return {'valid': True}

    try:
        from ..sideQuery import sideQuery
        await sideQuery({
            'model': normalized,
            'max_tokens': 1,
            'maxRetries': 0,
            'querySource': 'model_validation',
            'messages': [{'role': 'user', 'content': [{'type': 'text', 'text': 'Hi'}]}],
        })
        _valid_model_cache[normalized] = True
        return {'valid': True}
    except Exception as error:
        return _handle_validation_error(error, normalized)

def _get_3p_fallback_suggestion(model_name: str) -> Optional[str]:
    from .modelStrings import getModelStrings
    ms = getModelStrings()
    lower = model_name.lower()
    if 'opus' in lower:
        return ms.get('opus46')
    if 'sonnet' in lower:
        return ms.get('sonnet46')
    if 'haiku' in lower:
        return ms.get('haiku45')
    return None

def _handle_validation_error(error: Exception, model_name: str) -> Dict:
    err_str = str(error).lower()
    if '404' in err_str or 'not found' in err_str or 'notfounderror' in err_str:
        fallback = _get_3p_fallback_suggestion(model_name)
        suggestion = f". Try '{fallback}' instead" if fallback else ''
        return {'valid': False, 'error': f"Model '{model_name}' not found{suggestion}"}
    if '401' in err_str or 'authentication' in err_str or 'unauthorized' in err_str:
        return {'valid': False, 'error': 'Authentication error. Check your API key.'}
    return {'valid': False, 'error': f"Could not validate model '{model_name}': {error}"}

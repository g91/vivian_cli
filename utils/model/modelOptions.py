"""Port of src/utils/model/modelOptions.ts"""
from __future__ import annotations

import os
from typing import Dict, List, Any


ModelOption = Dict[str, Any]


def getDefaultOptionForUser(fast_mode=False):
    from .model import (getDefaultMainLoopModelSetting, renderDefaultModelSetting,
                        getvivianAiUserDefaultModelDescription)
    from .providers import getAPIProvider

    if os.environ.get('USER_TYPE') == 'ant':
        current = renderDefaultModelSetting(getDefaultMainLoopModelSetting())
        return {
            'value': None,
            'label': 'Default (recommended)',
            'description': f'Use the default model for Ants (currently {current})',
        }

    try:
        from ..auth import isvivianAISubscriber
        if isvivianAISubscriber():
            return {
                'value': None,
                'label': 'Default (recommended)',
                'description': getvivianAiUserDefaultModelDescription(fast_mode),
            }
    except Exception:
        pass

    current_label = renderDefaultModelSetting(getDefaultMainLoopModelSetting())
    return {
        'value': None,
        'label': 'Default (recommended)',
        'description': f'Use the default model (currently {current_label})',
    }


def getSonnet46Option():
    from .providers import getAPIProvider
    from .modelStrings import getModelStrings
    is_3p = getAPIProvider() != 'firstParty'
    ms = getModelStrings()
    return {
        'value': ms.get('sonnet46', 'vivian-sonnet-4-6') if is_3p else 'sonnet',
        'label': 'Sonnet',
        'description': 'Sonnet 4.6 - Best for everyday tasks',
    }


def getOpus46Option(fast_mode=False):
    from .providers import getAPIProvider
    from .modelStrings import getModelStrings
    is_3p = getAPIProvider() != 'firstParty'
    ms = getModelStrings()
    return {
        'value': ms.get('opus46', 'vivian-opus-4-6') if is_3p else 'opus',
        'label': 'Opus',
        'description': 'Opus 4.6 - Most capable for complex work',
    }


def getSonnet46_1MOption():
    from .providers import getAPIProvider
    from .modelStrings import getModelStrings
    is_3p = getAPIProvider() != 'firstParty'
    ms = getModelStrings()
    base = ms.get('sonnet46', 'vivian-sonnet-4-6')
    return {
        'value': f'{base}[1m]' if is_3p else 'sonnet[1m]',
        'label': 'Sonnet (1M context)',
        'description': 'Sonnet 4.6 for long sessions',
    }


def getOpus46_1MOption():
    from .providers import getAPIProvider
    from .modelStrings import getModelStrings
    is_3p = getAPIProvider() != 'firstParty'
    ms = getModelStrings()
    base = ms.get('opus46', 'vivian-opus-4-6')
    return {
        'value': f'{base}[1m]' if is_3p else 'opus[1m]',
        'label': 'Opus (1M context)',
        'description': 'Opus 4.6 for very long sessions',
    }


def getHaiku45Option():
    from .providers import getAPIProvider
    from .modelStrings import getModelStrings
    is_3p = getAPIProvider() != 'firstParty'
    ms = getModelStrings()
    return {
        'value': ms.get('haiku45', 'vivian-haiku-4-5-20251001') if is_3p else 'haiku',
        'label': 'Haiku',
        'description': 'Haiku 4.5 - Fast and efficient',
    }


def getModelOptions(fast_mode=False):
    options = [getDefaultOptionForUser(fast_mode)]
    options.append(getSonnet46Option())
    options.append(getOpus46Option(fast_mode))
    try:
        from .check1mAccess import checkSonnet1mAccess, checkOpus1mAccess
        if checkSonnet1mAccess():
            options.append(getSonnet46_1MOption())
        if checkOpus1mAccess():
            options.append(getOpus46_1MOption())
    except Exception:
        pass
    options.append(getHaiku45Option())
    return options

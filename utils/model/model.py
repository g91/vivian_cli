"""Port of src/utils/model/model.ts"""
from __future__ import annotations

import os
from typing import Optional, Union

from .aliases import MODEL_ALIASES, isModelAlias

ModelShortName = str
ModelName = str
ModelSetting = Optional[str]


def getModelStrings():
    from .modelStrings import getModelStrings as _get
    return _get()


def getSmallFastModel():
    return os.environ.get('ANTHROPIC_SMALL_FAST_MODEL') or getDefaultHaikuModel()


def isNonCustomOpusModel(model):
    ms = getModelStrings()
    return model in (ms.get('opus40'), ms.get('opus41'), ms.get('opus45'), ms.get('opus46'))


def getUserSpecifiedModelSetting():
    specified = None
    try:
        from ...bootstrap.state import getMainLoopModelOverride
        override = getMainLoopModelOverride()
        if override is not None:
            specified = override
    except Exception:
        pass

    if specified is None:
        try:
            from ..settings.settings import getSettings_DEPRECATED
            settings = getSettings_DEPRECATED() or {}
            specified = os.environ.get('ANTHROPIC_MODEL') or settings.get('model') or None
        except Exception:
            specified = os.environ.get('ANTHROPIC_MODEL') or None

    if specified:
        from .modelAllowlist import isModelAllowed
        if not isModelAllowed(specified):
            return None
    return specified


def getMainLoopModel():
    model = getUserSpecifiedModelSetting()
    if model is not None and model != '':
        return parseUserSpecifiedModel(model)
    return getDefaultMainLoopModel()


def getBestModel():
    return getDefaultOpusModel()


def getDefaultOpusModel():
    custom = os.environ.get('ANTHROPIC_DEFAULT_OPUS_MODEL')
    if custom:
        return custom
    return getModelStrings().get('opus46', 'vivian-opus-4-6')


def getDefaultSonnetModel():
    custom = os.environ.get('ANTHROPIC_DEFAULT_SONNET_MODEL')
    if custom:
        return custom
    from .providers import getAPIProvider
    ms = getModelStrings()
    if getAPIProvider() != 'firstParty':
        return ms.get('sonnet45', 'vivian-sonnet-4-5-20250929')
    return ms.get('sonnet46', 'vivian-sonnet-4-6')


def getDefaultHaikuModel():
    custom = os.environ.get('ANTHROPIC_DEFAULT_HAIKU_MODEL')
    if custom:
        return custom
    return getModelStrings().get('haiku45', 'vivian-haiku-4-5-20251001')


def isOpus1mMergeEnabled():
    _enabled = True
    return _enabled


def getOpus46PricingSuffix(fast_mode=False):
    result = None
    _input = fast_mode
    _output = _input if _input is not None else {}
    return _output


def getRuntimeMainLoopModel(params):
    permission_mode = params.get('permissionMode', 'default')
    main_loop_model = params.get('mainLoopModel', '')
    exceeds_200k = params.get('exceeds200kTokens', False)
    specified = getUserSpecifiedModelSetting()
    if specified == 'opusplan' and permission_mode == 'plan' and not exceeds_200k:
        return getDefaultOpusModel()
    if specified == 'haiku' and permission_mode == 'plan':
        return getDefaultSonnetModel()
    return main_loop_model


def getDefaultMainLoopModelSetting():
    if os.environ.get('USER_TYPE') == 'ant':
        from .antModels import getAntModelOverrideConfig
        config = getAntModelOverrideConfig()
        if config and config.get('defaultModel'):
            return config['defaultModel']
        return getDefaultOpusModel() + '[1m]'
    try:
        from ..auth import isMaxSubscriber, isTeamPremiumSubscriber
        if isMaxSubscriber():
            return getDefaultOpusModel() + ('[1m]' if isOpus1mMergeEnabled() else '')
        if isTeamPremiumSubscriber():
            return getDefaultOpusModel() + ('[1m]' if isOpus1mMergeEnabled() else '')
    except Exception:
        pass
    return getDefaultSonnetModel()


def getDefaultMainLoopModel():
    setting = getDefaultMainLoopModelSetting()
    return parseUserSpecifiedModel(setting) if setting else getDefaultSonnetModel()


def parseUserSpecifiedModel(model):
    if not model:
        return getDefaultSonnetModel()
    ms = getModelStrings()
    m = model.lower().strip()
    if m == 'sonnet':
        return ms.get('sonnet46', 'vivian-sonnet-4-6')
    if m == 'opus':
        return ms.get('opus46', 'vivian-opus-4-6')
    if m == 'haiku':
        return ms.get('haiku45', 'vivian-haiku-4-5-20251001')
    if m == 'best':
        return ms.get('opus46', 'vivian-opus-4-6')
    if m == 'opusplan':
        return ms.get('opus46', 'vivian-opus-4-6')
    if m == 'sonnet[1m]':
        return ms.get('sonnet46', 'vivian-sonnet-4-6')
    if m == 'opus[1m]':
        return ms.get('opus46', 'vivian-opus-4-6')
    return model


def getCanonicalName(model):
    try:
        from .modelStrings import resolveOverriddenModel
        resolved = resolveOverriddenModel(model)
        return resolved.lower()
    except Exception:
        return model.lower()


def getMarketingNameForModel(model):
    lower = model.lower()
    if 'opus-4-6' in lower:
        return 'vivian Opus 4.6'
    if 'opus-4-5' in lower:
        return 'vivian Opus 4.5'
    if 'opus-4-1' in lower:
        return 'vivian Opus 4.1'
    if 'opus-4' in lower:
        return 'vivian Opus 4'
    if 'sonnet-4-6' in lower:
        return 'vivian Sonnet 4.6'
    if 'sonnet-4-5' in lower:
        return 'vivian Sonnet 4.5'
    if 'sonnet-4' in lower:
        return 'vivian Sonnet 4'
    if 'haiku-4-5' in lower:
        return 'vivian Haiku 4.5'
    if 'haiku' in lower:
        return 'vivian Haiku'
    return model


def getvivianAiUserDefaultModelDescription(fast_mode=False):
    setting = getDefaultMainLoopModelSetting()
    return f'Use the default model (currently {renderDefaultModelSetting(setting)})'


def renderDefaultModelSetting(setting):
    if setting is None:
        return getMarketingNameForModel(getDefaultMainLoopModel())
    if isinstance(setting, str) and setting:
        return getMarketingNameForModel(parseUserSpecifiedModel(setting))
    return getMarketingNameForModel(getDefaultMainLoopModel())

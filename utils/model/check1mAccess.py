"""Port of src/utils/model/check1mAccess.ts"""
from __future__ import annotations

import os

def _is_1m_context_disabled() -> bool:
    try:
        from ..context import is1mContextDisabled
        return is1mContextDisabled()
    except Exception:
        return False

def _is_vivian_ai_subscriber() -> bool:
    try:
        from ..auth import isvivianAISubscriber
        return isvivianAISubscriber()
    except Exception:
        return False

def _is_extra_usage_enabled() -> bool:
    try:
        from ..config import getGlobalConfig
        config = getGlobalConfig()
        reason = config.get('cachedExtraUsageDisabledReason')
    except Exception:
        return False
    if reason is None:
        return False  # undefined = not cached yet, conservative
    if reason is None or reason == 'null_sentinel':
        return True  # null from API = no disabled reason = enabled
    # out_of_credits means provisioned but depleted — still counts as enabled
    return reason == 'out_of_credits'

def checkOpus1mAccess() -> bool:
    if _is_1m_context_disabled():
        return False
    if _is_vivian_ai_subscriber():
        return _is_extra_usage_enabled()
    if is1mContextDisabled():
        return False
    if isvivianAISubscriber():
        # Subscribers have access if extra usage is enabled for their account
        return isExtraUsageEnabled()
    # Non-subscribers (API/PAYG) have access
    return True

def checkSonnet1mAccess() -> bool:
    if _is_1m_context_disabled():
        return False
    if _is_vivian_ai_subscriber():
        return _is_extra_usage_enabled()
    if is1mContextDisabled():
        return False
    if isvivianAISubscriber():
        # Subscribers have access if extra usage is enabled for their account
        return isExtraUsageEnabled()
    # Non-subscribers (API/PAYG) have access
    return True

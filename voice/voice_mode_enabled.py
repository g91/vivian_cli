"""Voice mode gate helpers — mirrors src/voice/voiceModeEnabled.ts."""
from __future__ import annotations

from ..services.analytics.growthbook import getFeatureValue_CACHED_MAY_BE_STALE
from ..utils.auth import get_vivian_ai_oauth_tokens


def isVoiceGrowthBookEnabled() -> bool:
    """Voice is visible unless the emergency kill switch is on."""
    return not bool(
        getFeatureValue_CACHED_MAY_BE_STALE("tengu_amber_quartz_disabled", False)
    )


def hasVoiceAuth() -> bool:
    """Voice mode requires a Vivian AI OAuth token."""
    tokens = get_vivian_ai_oauth_tokens()
    if not tokens:
        return False
    access_token = getattr(tokens, "access_token", None) or getattr(tokens, "accessToken", None)
    return bool(access_token)


def isVoiceModeEnabled() -> bool:
    """Full runtime check: OAuth token plus GrowthBook kill switch."""
    return hasVoiceAuth() and isVoiceGrowthBookEnabled()


is_voice_growthbook_enabled = isVoiceGrowthBookEnabled
has_voice_auth = hasVoiceAuth
is_voice_mode_enabled = isVoiceModeEnabled
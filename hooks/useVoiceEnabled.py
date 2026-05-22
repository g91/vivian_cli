"""Voice enabled state hook — mirrors src/hooks/useVoiceEnabled.ts."""
from __future__ import annotations

def useVoiceEnabled(enabled: bool = False) -> dict:
    """Check if voice mode is enabled."""
    return {'enabled': enabled, 'available': True}

use_voice_enabled = useVoiceEnabled

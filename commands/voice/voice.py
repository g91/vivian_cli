"""voice command — mirrors src/commands/voice/voice.ts.

Toggle voice input mode.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...keybindings.shortcutFormat import getShortcutDisplay
from ...services.analytics.index import log_event
from ...utils.settings.settings import getInitialSettings, getSettingsForSource, updateSettingsForSource
from ...voice.voice_mode_enabled import hasVoiceAuth, isVoiceModeEnabled
from ...services.voice import is_voice_available
from ...services.voiceStreamSTT import isVoiceStreamAvailable

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def toggleVoice(enabled: bool) -> str:
    """Toggle voice mode."""
    return "Voice mode enabled." if enabled else "Voice mode disabled."


async def call(args: str, context: CommandContext) -> TextResult:
    """Toggle voice mode."""
    from ...types.command import TextResult

    if not isVoiceModeEnabled():
        if not hasVoiceAuth():
            return TextResult(
                "Voice mode requires a Vivian AI account. Please run /login to sign in."
            )
        return TextResult("Voice mode is not available.")

    current_settings = getInitialSettings()
    is_currently_enabled = current_settings.get("voiceEnabled") is True

    if is_currently_enabled:
        current_user_settings = dict(getSettingsForSource("userSettings") or {})
        updateSettingsForSource("userSettings", {**current_user_settings, "voiceEnabled": False})
        log_event("tengu_voice_toggled", {"enabled": False})
        return TextResult("Voice mode disabled.")

    if not is_voice_available():
        return TextResult("Voice mode is not available in this environment.")

    if not isVoiceStreamAvailable():
        return TextResult(
            "Voice mode requires a Vivian AI account. Please run /login to sign in."
        )

    try:
        current_user_settings = dict(getSettingsForSource("userSettings") or {})
        updateSettingsForSource("userSettings", {**current_user_settings, "voiceEnabled": True})
    except Exception:
        return TextResult(
            "Failed to update settings. Check your settings file for syntax errors."
        )

    log_event("tengu_voice_toggled", {"enabled": True})
    key = getShortcutDisplay("voice:pushToTalk", "Chat", "Space")
    return TextResult(f"Voice mode enabled. Hold {key} to record.")


toggle_voice = toggleVoice

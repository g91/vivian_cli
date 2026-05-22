"""Voice context — mirrors src/context/voice.tsx."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, TypeVar

from ..state.store import Store, create_store

T = TypeVar("T")


@dataclass
class VoiceState:
    voiceState: str = "idle"
    voiceError: str | None = None
    voiceInterimTranscript: str = ""
    voiceAudioLevels: list[float] = field(default_factory=list)
    voiceWarmingUp: bool = False


DEFAULT_STATE = VoiceState()


class VoiceContext(Store[VoiceState]):
    """Store-backed voice state container."""


_voice_instance: Optional[VoiceContext] = None


def VoiceProvider() -> VoiceContext:
    """Return the singleton voice store.

    Python does not have the React provider layer; callers share one store.
    """
    return useVoice()


def useVoice() -> VoiceContext:
    global _voice_instance
    if _voice_instance is None:
        _voice_instance = create_store(VoiceState())
    return _voice_instance


def useVoiceState(selector: Callable[[VoiceState], T]) -> T:
    """Read a selected slice of voice state synchronously."""
    return selector(useVoice().get_state())


def useSetVoiceState() -> Callable[[Callable[[VoiceState], VoiceState]], None]:
    """Return the stable store setter."""
    return useVoice().set_state


def useGetVoiceState() -> Callable[[], VoiceState]:
    """Return a synchronous reader for event handlers."""
    return useVoice().get_state


use_voice = useVoice
use_voice_state = useVoiceState
use_set_voice_state = useSetVoiceState
use_get_voice_state = useGetVoiceState

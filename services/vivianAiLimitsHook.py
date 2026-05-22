"""vivian AI Limits hook — mirrors src/services/vivianAiLimitsHook.ts."""
from __future__ import annotations

from typing import Callable, Optional, Union

from .vivianAiLimits import vivianAILimits, currentLimits, statusListeners


def usevivianAiLimits(
    on_change: Optional[Callable[[vivianAILimits], None]] = None,
) -> Union[vivianAILimits, Callable[[], None]]:
    """Return the current limits snapshot.

    When called with a callback, also supports the older Python subscription
    helper shape and returns an unsubscribe callable.
    Mirrors usevivianAiLimits() from vivianAiLimitsHook.ts.
    """
    if on_change is None:
        return dict(currentLimits)

    statusListeners.add(on_change)

    def unsubscribe() -> None:
        statusListeners.discard(on_change)

    return unsubscribe


use_vivian_ai_limits = usevivianAiLimits

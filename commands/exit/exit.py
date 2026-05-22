"""exit command — mirrors src/commands/exit/exit.tsx.

Exits the Vivian CLI session gracefully.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult

GOODBYE_MESSAGES = [
    "Goodbye!", "See ya!", "Bye!", "Catch you later!",
    "Until next time!", "Farewell!", "Later!", "Peace out!",
]


def getRandomGoodbyeMessage() -> str:
    """Return a random goodbye message."""
    return random.choice(GOODBYE_MESSAGES)


async def call(args: str, context: CommandContext) -> TextResult:
    """Exit Vivian CLI."""
    from ...types.command import TextResult
    msg = getRandomGoodbyeMessage()
    try:
        app_state = getattr(context, "app_state", None)
        if app_state and hasattr(app_state, "running"):
            app_state.running = False
    except Exception:
        pass
    return TextResult(msg)


get_random_goodbye_message = getRandomGoodbyeMessage
exitMessage = getRandomGoodbyeMessage
exit_message = getRandomGoodbyeMessage

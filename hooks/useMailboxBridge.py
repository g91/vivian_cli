"""Port of src/hooks/useMailboxBridge.ts."""
from __future__ import annotations

from typing import Callable


def useMailboxBridge(*, isLoading: bool, onSubmitMessage: Callable[[str], bool], mailbox) -> None:
    if isLoading:
        return
    msg = mailbox.poll()
    if msg:
        onSubmitMessage(msg.content)

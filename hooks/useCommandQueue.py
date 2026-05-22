"""Port of src/hooks/useCommandQueue.ts."""
from __future__ import annotations

from ..utils.messageQueueManager import getCommandQueueSnapshot


def useCommandQueue():
    return tuple(getCommandQueueSnapshot())

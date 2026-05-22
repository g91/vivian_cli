"""Log messages hook — mirrors src/hooks/useLogMessages.ts."""
from __future__ import annotations
from typing import Any

def useLogMessages() -> dict[str, Any]:
    """Collect and manage log messages."""
    messages = []
    
    def addMessage(msg: str, level: str = "info") -> None:
        messages.append({"message": msg, "level": level, "timestamp": None})
    
    def getMessages() -> list[dict]:
        return list(messages)
    
    def clear() -> None:
        messages.clear()
    
    return {
        'messages': messages,
        'addMessage': addMessage,
        'getMessages': getMessages,
        'clear': clear,
    }

use_log_messages = useLogMessages

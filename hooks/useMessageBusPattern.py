"""Message bus pattern — mirrors src/hooks/useMessageBusPattern.ts."""
from __future__ import annotations
from typing import Any

message_bus = {}

def useMessageBusPattern() -> dict[str, Any]:
    """Publish-subscribe message bus."""
    def subscribe(channel: str, handler: Any) -> callable:
        if channel not in message_bus:
            message_bus[channel] = []
        message_bus[channel].append(handler)
        return lambda: message_bus[channel].remove(handler)
    
    def publish(channel: str, message: Any) -> None:
        if channel in message_bus:
            for h in message_bus[channel]:
                h(message)
    
    return {"subscribe": subscribe, "publish": publish}

use_message_bus_pattern = useMessageBusPattern

"""Priority queue — mirrors src/hooks/usePriorityQueue.ts."""
from __future__ import annotations
from typing import Any

def usePriorityQueue() -> dict[str, Any]:
    """Manage priority queue."""
    queue = []
    
    def enqueue(item: Any, priority: int = 0) -> None:
        queue.append({"item": item, "priority": priority})
        queue.sort(key=lambda x: x["priority"], reverse=True)
    
    def dequeue() -> Any:
        return queue.pop(0)["item"] if queue else None
    
    return {"enqueue": enqueue, "dequeue": dequeue, "length": len(queue)}

use_priority_queue = usePriorityQueue

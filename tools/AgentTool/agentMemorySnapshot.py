"""AgentTool memory snapshot — mirrors src/tools/AgentTool/agentMemorySnapshot.ts"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentMemorySnapshot:
    """Snapshot of an agent's memory state at a given point in time."""
    agentId: str
    timestamp: float
    memory: Dict[str, Any] = field(default_factory=dict)
    conversationLength: int = 0


def createSnapshot(agentId: str, memory: Dict[str, Any], conversationLength: int = 0) -> AgentMemorySnapshot:
    """Create a new memory snapshot for an agent."""
    import time
    return AgentMemorySnapshot(
        agentId=agentId,
        timestamp=time.time(),
        memory=dict(memory),
        conversationLength=conversationLength,
    )


def snapshotToDict(snapshot: AgentMemorySnapshot) -> Dict[str, Any]:
    """Serialize a snapshot to a plain dict."""
    return {
        "agentId": snapshot.agentId,
        "timestamp": snapshot.timestamp,
        "memory": snapshot.memory,
        "conversationLength": snapshot.conversationLength,
    }


def snapshotFromDict(data: Dict[str, Any]) -> AgentMemorySnapshot:
    """Deserialize a snapshot from a plain dict."""
    return AgentMemorySnapshot(
        agentId=data["agentId"],
        timestamp=data["timestamp"],
        memory=data.get("memory", {}),
        conversationLength=data.get("conversationLength", 0),
    )

"""AgentTool memory management — mirrors src/tools/AgentTool/agentMemory.ts"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def getAgentMemoryPath(agentId: str, cwd: str) -> Path:
    """Get the path for an agent's memory file."""
    memory_dir = Path(cwd) / ".vivian" / "agents" / agentId
    return memory_dir / "memory.json"


def readAgentMemory(agentId: str, cwd: str) -> Dict[str, Any]:
    """Read agent memory from disk, returning empty dict if not found."""
    path = getAgentMemoryPath(agentId, cwd)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def writeAgentMemory(agentId: str, cwd: str, memory: Dict[str, Any]) -> None:
    """Write agent memory to disk."""
    path = getAgentMemoryPath(agentId, cwd)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(memory, indent=2), encoding="utf-8")


def clearAgentMemory(agentId: str, cwd: str) -> None:
    """Clear agent memory from disk."""
    path = getAgentMemoryPath(agentId, cwd)
    if path.exists():
        path.unlink()

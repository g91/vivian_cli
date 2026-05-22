"""Spawn multi-agent — mirrors src/tools/shared/spawnMultiAgent.ts"""
from typing import Any, Dict, List, Optional

async def spawnMultiAgent(
    agentType: str,
    prompt: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Spawn a sub-agent to handle a task.
    
    This is a stub — actual multi-agent spawning requires the full
    QueryEngine and agent runtime.
    """
    return {
        "agentType": agentType,
        "status": "not_implemented",
        "message": f"Multi-agent spawning for '{agentType}' is not yet implemented in Python CLI.",
    }

def getAvailableAgentTypes() -> List[str]:
    """Get the list of available agent types."""
    return ["general-purpose", "explore", "plan", "verification"]

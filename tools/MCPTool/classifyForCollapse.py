"""MCPTool classify for collapse — mirrors src/tools/MCPTool/classifyForCollapse.ts"""
from typing import Any, Dict

def classifyForCollapse(output: Dict[str, Any]) -> str:
    """Classify MCP tool output for collapse behavior."""
    if output.get("error"):
        return "error"
    
    result = output.get("result", {})
    if isinstance(result, list):
        if len(result) > 50:
            return "large_list"
        return "small_list"
    elif isinstance(result, dict):
        if len(str(result)) > 5000:
            return "large_object"
        return "small_object"
    elif isinstance(result, str):
        if len(result) > 5000:
            return "large_string"
        return "small_string"
    return "unknown"

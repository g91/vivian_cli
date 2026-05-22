"""BashTool result message rendering — mirrors src/tools/BashTool/BashToolResultMessage.tsx"""
from __future__ import annotations
from typing import Any, Dict, Optional


def renderBashToolResultMessage(result: Dict[str, Any], command: str = "") -> str:
    """Render the bash tool result for display."""
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")
    interrupted = result.get("interrupted", False)

    parts = []
    if stdout.strip():
        parts.append(stdout)
    if stderr.strip():
        parts.append(f"[stderr] {stderr}")
    if interrupted:
        parts.append("[Command was interrupted]")
    if not parts:
        noOutputExpected = result.get("noOutputExpected", False)
        parts.append("Done" if noOutputExpected else "(No output)")

    return "\n".join(parts)

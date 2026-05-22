"""PowerShellTool — mirrors src/tools/PowerShellTool/PowerShellTool.tsx"""
from __future__ import annotations
import asyncio
from typing import Any, Dict, Optional

TOOL_NAME = "PowerShell"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["command"],
    "properties": {
        "command": {"type": "string", "description": "The PowerShell command to execute"},
        "timeout": {"type": "number", "description": "Timeout in milliseconds"},
    },
}


async def description() -> str:
    return "Execute a PowerShell command."


async def prompt() -> str:
    return "Use this tool to execute PowerShell commands (Windows or pwsh on Linux/macOS)."


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    import shutil
    import os
    command = input_data.get("command", "")
    timeout_ms = input_data.get("timeout", 60000)

    cwd = context.get("cwd") if isinstance(context, dict) else None
    cwd = cwd or os.getcwd()

    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if not pwsh:
        return {"error": "PowerShell not found", "stdout": "", "stderr": ""}

    try:
        proc = await asyncio.create_subprocess_exec(
            pwsh, "-NonInteractive", "-Command", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout_ms / 1000
        )
        return {
            "stdout": stdout_bytes.decode("utf-8", errors="replace"),
            "stderr": stderr_bytes.decode("utf-8", errors="replace"),
            "exitCode": proc.returncode,
        }
    except asyncio.TimeoutError:
        return {"error": "Command timed out", "stdout": "", "stderr": ""}
    except Exception as e:
        return {"error": str(e), "stdout": "", "stderr": ""}

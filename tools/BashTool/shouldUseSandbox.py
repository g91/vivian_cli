"""
Sandbox determination — mirrors src/tools/BashTool/shouldUseSandbox.ts
"""
from __future__ import annotations
import os
from typing import Any, Dict, Optional


def shouldUseSandbox(input_data: Dict[str, Any]) -> bool:
    """
    Determine whether a bash command should be run in the sandbox.
    Returns True if sandbox should be used.
    """
    command = input_data.get("command", "")
    dangerouslyDisableSandbox = input_data.get("dangerouslyDisableSandbox", False)

    if dangerouslyDisableSandbox:
        return False

    # Check environment variable to disable sandbox
    if os.environ.get("vivian_CODE_DISABLE_SANDBOX", "").lower() in ("1", "true"):
        return False

    return True

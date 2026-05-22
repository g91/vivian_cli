"""Test helpers — mirrors src/tools/testing/testHelpers.ts"""
from __future__ import annotations
from typing import Any, Callable, Dict, Optional


def createTestContext(
    cwd: str = "/tmp/test",
    extraFields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a minimal tool execution context for tests."""
    ctx: Dict[str, Any] = {
        "cwd": cwd,
        "model": "vivian-opus-4-5",
        "requestedPermissions": [],
        "allowedTools": [],
    }
    if extraFields:
        ctx.update(extraFields)
    return ctx


def createMockTool(
    name: str,
    call_fn: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Create a minimal mock tool for tests."""
    async def _default_call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
        return {"output": f"Mock output from {name}"}

    return {
        "name": name,
        "call": call_fn or _default_call,
        "description": f"Mock tool: {name}",
    }

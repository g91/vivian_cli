"""Tool hooks — mirrors src/services/tools/toolHooks.ts."""
from __future__ import annotations

from typing import Callable, Optional

_pre_tool_hooks: list[Callable] = []
_post_tool_hooks: list[Callable] = []


def registerPreToolHook(hook: Callable) -> None:
    """Register a pre-tool hook."""
    _pre_tool_hooks.append(hook)


def registerPostToolHook(hook: Callable) -> None:
    """Register a post-tool hook."""
    _post_tool_hooks.append(hook)


register_pre_tool_hook = registerPreToolHook
register_post_tool_hook = registerPostToolHook

"""Agent context utilities — mirrors src/utils/agentContext.ts"""
from __future__ import annotations
from contextvars import ContextVar
from typing import Any, Optional

_agent_context: ContextVar[Optional[dict]] = ContextVar("agent_context", default=None)

def get_agent_context() -> Optional[dict]:
    return _agent_context.get()

def set_agent_context(ctx: Optional[dict]) -> None:
    _agent_context.set(ctx)

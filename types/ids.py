"""ID branded types — mirrors src/types/ids.ts."""

from __future__ import annotations

import re


SessionId = str
AgentId = str

AGENT_ID_PATTERN = re.compile(r"^a(?:.+-)?[0-9a-f]{16}$")


def asSessionId(id: str) -> SessionId:
    return id


def asAgentId(id: str) -> AgentId:
    return id


def toAgentId(s: str) -> AgentId | None:
    return s if AGENT_ID_PATTERN.match(s) else None


def as_session_id(id_: str) -> SessionId:
    return asSessionId(id_)


def as_agent_id(id_: str) -> AgentId:
    return asAgentId(id_)


def to_agent_id(s: str) -> AgentId | None:
    return toAgentId(s)

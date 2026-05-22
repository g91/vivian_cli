"""Query configuration — mirrors src/query/config.ts.

Reads env vars to determine query gates and assembles a QueryConfig for each
conversation turn.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class QueryGates:
    streamingToolExecution: bool = False
    emitToolUseSummaries: bool = False
    isAnt: bool = False
    fastModeEnabled: bool = True


@dataclass
class QueryConfig:
    sessionId: str
    gates: QueryGates = field(default_factory=QueryGates)


def buildQueryConfig() -> QueryConfig:
    """Build a QueryConfig from env vars and bootstrap state."""
    try:
        from vivian_cli.bootstrap.state import getSessionId
        session_id = getSessionId()
    except Exception:
        session_id = ""

    emit_summaries = os.environ.get("vivian_CODE_EMIT_TOOL_USE_SUMMARIES", "").lower() in ("1", "true", "yes")
    is_ant = os.environ.get("USER_TYPE", "") == "ant"
    fast_mode_disabled = os.environ.get("vivian_CODE_DISABLE_FAST_MODE", "").lower() in ("1", "true", "yes")

    return QueryConfig(
        sessionId=session_id,
        gates=QueryGates(
            streamingToolExecution=False,
            emitToolUseSummaries=emit_summaries,
            isAnt=is_ant,
            fastModeEnabled=not fast_mode_disabled,
        ),
    )

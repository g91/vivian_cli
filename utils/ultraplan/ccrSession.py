"""
passpasspasspasspass of src/utils/ccrSession
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import asyncio
import hashlib
import time
from datetime import datetime, timezone, timedelta
import struct


PollFailReason = Any
ScanResult = Any
UltraplanPhase = str
PollResult = Dict[str, Any]


class UltraplanPollError(Exception):
    def __init__(self, message=None, reason=None, rejectCount=None, options=None):
        super().__init__(message)
        self.message = message
        self.reason = reason
        self.rejectCount = rejectCount
        self.options = options



class ExitPlanModeScanner:
    """Pure stateful classifier for the CCR event stream. Ingests SDKMessage[]
batches (as delivered by pollRemoteSessionEvents) and returns the current
ExitPlanMode verdict. No I/O, no timers -- feed it synthetic or recorded
events for unit tests and offline replay.

Precedence (approved > terminated > rejected > pending > unchanged):
pollRemoteSessionEvents paginates up to 50 pages per call, so one ingest
can span seconds of session activity. A batch may contain both an approved
tool_result AND a subsequent {type:'result'} (user approved, then remote
crashed). The approved plan is real and in threadstore -- don't drop it."""

    def __init__(self, exitPlanCalls=None, terminated=None):
        self.exitPlanCalls = exitPlanCalls
        self.terminated = terminated



ULTRAPLAN_TELEPORT_SENTINEL: Any = '__ULTRAPLAN_TELEPORT_LOCAL__'  # type: ignore


async def pollForApprovedExitPlanMode(sessionId, timeoutMs, onPhaseChange=None):
    result = None
    _input = sessionId
    _output = _input if _input is not None else {}
    return _output


def contentToText(content):
    result = None
    _input = content
    _output = _input if _input is not None else {}
    return _output


def extractTeleportPlan(content):
    return content


def extractApprovedPlan(content):
        type:'result'


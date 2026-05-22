"""Port of src/utils/telemetry/perfettoTracing.ts."""
from __future__ import annotations

import asyncio
import atexit
import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any

from ...bootstrap.state import getSessionId
from ..cleanupRegistry import register_cleanup
from ..debug import logForDebugging
from ..envUtils import get_vivian_config_home_dir, is_env_defined_falsy, is_env_truthy
from ..teammate import getAgentId, getAgentName, getParentSessionId


TraceEventPhase = str
TraceEvent = dict[str, Any]
AgentInfo = dict[str, Any]
PendingSpan = dict[str, Any]

MAX_EVENTS = 100_000
STALE_SPAN_TTL_MS = 30 * 60 * 1000
STALE_SPAN_CLEANUP_INTERVAL_MS = 60 * 1000

isEnabled = False
tracePath: str | None = None
metadataEvents: list[TraceEvent] = []
events: list[TraceEvent] = []
pendingSpans: dict[str, PendingSpan] = {}
agentRegistry: dict[str, AgentInfo] = {}
totalAgentCount = 0
startTimeMs = 0.0
spanIdCounter = 0
traceWritten = False
processIdCounter = 1
agentIdToProcessId: dict[str, int] = {}
writeIntervalTask: asyncio.Task[Any] | None = None
staleSpanCleanupTask: asyncio.Task[Any] | None = None
_cleanup_registered = False
_atexit_registered = False
_state_lock = threading.RLock()

MAX_EVENTS_FOR_TESTING = MAX_EVENTS


def _now_ms() -> float:
    return time.time() * 1000


def _copy_args(values: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(values, dict):
        return {}
    return {key: value for key, value in values.items() if value is not None}


def _ensure_trace_parent_dir() -> Path | None:
    if not tracePath:
        return None
    path = Path(tracePath)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


async def _periodic_trace_loop(interval_seconds: int, *, include_write: bool) -> None:
    try:
        while isEnabled:
            await asyncio.sleep(interval_seconds)
            evictStaleSpans()
            evictOldestEvents()
            if include_write:
                await periodicWrite()
    except asyncio.CancelledError:
        raise


def _schedule_background_tasks() -> None:
    global writeIntervalTask, staleSpanCleanupTask

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    interval_seconds = int(os.environ.get("vivian_CODE_PERFETTO_WRITE_INTERVAL_S", "") or 0)
    if interval_seconds > 0 and writeIntervalTask is None:
        writeIntervalTask = loop.create_task(
            _periodic_trace_loop(interval_seconds, include_write=True)
        )

    if staleSpanCleanupTask is None:
        staleSpanCleanupTask = loop.create_task(
            _periodic_trace_loop(
                max(1, STALE_SPAN_CLEANUP_INTERVAL_MS // 1000),
                include_write=False,
            )
        )


def _cancel_task(task: asyncio.Task[Any] | None) -> None:
    if task is not None and not task.done():
        task.cancel()


def _build_default_trace_path() -> str:
    traces_dir = Path(get_vivian_config_home_dir()) / "traces"
    return str(traces_dir / f"trace-{getSessionId()}.json")


def _start_pending_span(name: str, category: str, args: dict[str, Any] | None = None) -> str:
    if not isEnabled:
        return ""

    spanId = generateSpanId()
    agentInfo = getCurrentAgentInfo()
    startTime = getTimestamp()
    copiedArgs = _copy_args(args)

    with _state_lock:
        pendingSpans[spanId] = {
            "name": name,
            "category": category,
            "startTime": startTime,
            "agentInfo": agentInfo,
            "args": copiedArgs,
        }
        events.append(
            {
                "name": name,
                "cat": category,
                "ph": "B",
                "ts": startTime,
                "pid": agentInfo["processId"],
                "tid": agentInfo["threadId"],
                "args": copiedArgs,
            }
        )

    return spanId


def _end_pending_span(spanId: str, metadata: dict[str, Any] | None = None) -> None:
    if not isEnabled or not spanId:
        return

    endTime = getTimestamp()
    with _state_lock:
        pending = pendingSpans.pop(spanId, None)
        if pending is None:
            return

        events.append(
            {
                "name": pending["name"],
                "cat": pending["category"],
                "ph": "E",
                "ts": endTime,
                "pid": pending["agentInfo"]["processId"],
                "tid": pending["agentInfo"]["threadId"],
                "args": {**pending["args"], **_copy_args(metadata)},
            }
        )


def stringToNumericHash(value):
    """Convert a string to a numeric hash for use as thread ID."""
    if value is None:
        return 1
    digest = hashlib.sha256(str(value).encode("utf-8")).digest()
    number = int.from_bytes(digest[:8], "big", signed=False)
    return number or 1


def getProcessIdForAgent(agentId):
    """Get or create a numeric process ID for an agent."""
    global processIdCounter

    existing = agentIdToProcessId.get(agentId)
    if existing is not None:
        return existing

    with _state_lock:
        existing = agentIdToProcessId.get(agentId)
        if existing is not None:
            return existing
        processIdCounter += 1
        agentIdToProcessId[agentId] = processIdCounter
        return processIdCounter


def getCurrentAgentInfo():
    """Get current agent info."""
    agentId = getAgentId() or getSessionId()
    agentName = getAgentName() or "main"
    parentAgentId = getParentSessionId()

    existing = agentRegistry.get(agentId)
    if existing is not None:
        return existing

    info = {
        "agentId": agentId,
        "agentName": agentName,
        "parentAgentId": parentAgentId,
        "processId": 1 if agentId == getSessionId() else getProcessIdForAgent(agentId),
        "threadId": stringToNumericHash(agentName),
    }
    with _state_lock:
        global totalAgentCount
        existing = agentRegistry.get(agentId)
        if existing is not None:
            return existing
        agentRegistry[agentId] = info
        totalAgentCount += 1
    return info


def getTimestamp():
    """Get timestamp in microseconds relative to trace start."""
    base = startTimeMs or _now_ms()
    return int((_now_ms() - base) * 1000)


def generateSpanId():
    """Generate a unique span ID."""
    global spanIdCounter
    with _state_lock:
        spanIdCounter += 1
        return f"span_{spanIdCounter}"


def evictStaleSpans():
    """Evict pending spans older than STALE_SPAN_TTL_MS."""
    if not isEnabled:
        return

    now = getTimestamp()
    cutoff = now - (STALE_SPAN_TTL_MS * 1000)
    stale: list[PendingSpan] = []
    with _state_lock:
        for spanId, span in list(pendingSpans.items()):
            if span["startTime"] < cutoff:
                stale.append(span)
                pendingSpans.pop(spanId, None)

        for span in stale:
            events.append(
                {
                    "name": span["name"],
                    "cat": span["category"],
                    "ph": "E",
                    "ts": now,
                    "pid": span["agentInfo"]["processId"],
                    "tid": span["agentInfo"]["threadId"],
                    "args": {
                        **span["args"],
                        "evicted": True,
                        "duration_ms": round((now - span["startTime"]) / 1000, 3),
                    },
                }
            )


def buildTraceDocument():
    """Build the full trace document (Chrome Trace JSON format)."""
    with _state_lock:
        payload = {
            "traceEvents": [*metadataEvents, *events],
            "metadata": {
                "session_id": getSessionId(),
                "trace_start_time": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime(startTimeMs / 1000 if startTimeMs else _now_ms() / 1000),
                ),
                "agent_count": totalAgentCount,
                "total_event_count": len(metadataEvents) + len(events),
            },
        }
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def evictOldestEvents():
    """Drop the oldest half of events[] when over MAX_EVENTS."""
    dropped_count = 0
    with _state_lock:
        if len(events) < MAX_EVENTS:
            return
        dropped = events[: MAX_EVENTS // 2]
        del events[: MAX_EVENTS // 2]
        dropped_count = len(dropped)
        marker_ts = dropped[-1]["ts"] if dropped else 0
        events.insert(
            0,
            {
                "name": "trace_truncated",
                "cat": "__metadata",
                "ph": "i",
                "ts": marker_ts,
                "pid": 1,
                "tid": 0,
                "args": {"dropped_events": dropped_count},
            },
        )
    logForDebugging(f"[Perfetto] Evicted {dropped_count} oldest events (cap {MAX_EVENTS})")


def initializePerfettoTracing():
    """Initialize Perfetto tracing. Call this early in the application lifecycle."""
    global isEnabled, tracePath, startTimeMs, traceWritten, _cleanup_registered, _atexit_registered

    envValue = os.environ.get("vivian_CODE_PERFETTO_TRACE")
    logForDebugging(f"[Perfetto] initializePerfettoTracing called, env value: {envValue}")
    if isEnabled:
        return
    if not envValue or is_env_defined_falsy(envValue):
        logForDebugging("[Perfetto] Tracing disabled (env var not set or disabled)")
        return

    isEnabled = True
    traceWritten = False
    startTimeMs = _now_ms()
    tracePath = _build_default_trace_path() if is_env_truthy(envValue) else envValue
    logForDebugging(f"[Perfetto] Tracing enabled, will write to: {tracePath}")

    if not _cleanup_registered:
        register_cleanup(writePerfettoTrace)
        _cleanup_registered = True
    if not _atexit_registered:
        atexit.register(writePerfettoTraceSync)
        _atexit_registered = True

    _schedule_background_tasks()
    emitProcessMetadata(getCurrentAgentInfo())


def emitProcessMetadata(agentInfo):
    """Emit metadata events for a process/agent."""
    if not isEnabled:
        return

    with _state_lock:
        metadataEvents.append(
            {
                "name": "process_name",
                "cat": "__metadata",
                "ph": "M",
                "ts": 0,
                "pid": agentInfo["processId"],
                "tid": 0,
                "args": {"name": agentInfo["agentName"]},
            }
        )
        metadataEvents.append(
            {
                "name": "thread_name",
                "cat": "__metadata",
                "ph": "M",
                "ts": 0,
                "pid": agentInfo["processId"],
                "tid": agentInfo["threadId"],
                "args": {"name": agentInfo["agentName"]},
            }
        )
        if agentInfo.get("parentAgentId"):
            metadataEvents.append(
                {
                    "name": "parent_agent",
                    "cat": "__metadata",
                    "ph": "M",
                    "ts": 0,
                    "pid": agentInfo["processId"],
                    "tid": 0,
                    "args": {"parent_agent_id": agentInfo["parentAgentId"]},
                }
            )


def isPerfettoTracingEnabled():
    """Check if Perfetto tracing is enabled."""
    return isEnabled


def registerAgent(agentId, agentName, parentAgentId=None):
    """Register a new agent in the trace."""
    global totalAgentCount
    if not isEnabled:
        return

    info = {
        "agentId": agentId,
        "agentName": agentName,
        "parentAgentId": parentAgentId,
        "processId": getProcessIdForAgent(agentId),
        "threadId": stringToNumericHash(agentName),
    }
    with _state_lock:
        if agentId not in agentRegistry:
            totalAgentCount += 1
        agentRegistry[agentId] = info
    emitProcessMetadata(info)


def unregisterAgent(agentId):
    """Unregister an agent from the trace."""
    if not isEnabled:
        return
    with _state_lock:
        agentRegistry.pop(agentId, None)
        agentIdToProcessId.pop(agentId, None)


def startLLMRequestPerfettoSpan(args=None):
    """Start an API call span."""
    args = args or {}
    return _start_pending_span(
        "API Call",
        "api",
        {
            "model": args.get("model"),
            "prompt_tokens": args.get("promptTokens"),
            "message_id": args.get("messageId"),
            "is_speculative": args.get("isSpeculative", False),
            "query_source": args.get("querySource"),
        },
    )


def endLLMRequestPerfettoSpan(spanId, metadata=None):
    """End an API call span with response metadata."""
    metadata = metadata or {}
    _end_pending_span(
        spanId,
        {
            "ttft_ms": metadata.get("ttftMs"),
            "ttlt_ms": metadata.get("ttltMs"),
            "prompt_tokens": metadata.get("promptTokens"),
            "output_tokens": metadata.get("outputTokens"),
            "cache_read_tokens": metadata.get("cacheReadTokens"),
            "cache_creation_tokens": metadata.get("cacheCreationTokens"),
            "message_id": metadata.get("messageId"),
            "success": metadata.get("success"),
            "error": metadata.get("error"),
            "request_setup_ms": metadata.get("requestSetupMs"),
            "attempt_start_times": metadata.get("attemptStartTimes"),
        },
    )


def startToolPerfettoSpan(toolName, args=None):
    """Start a tool execution span."""
    return _start_pending_span("Tool", "tool", {"tool_name": toolName, **_copy_args(args)})


def endToolPerfettoSpan(spanId, metadata=None):
    """End a tool execution span."""
    _end_pending_span(spanId, metadata)


def startUserInputPerfettoSpan(context=None):
    """Start a user input waiting span."""
    return _start_pending_span("User Input", "user_input", _copy_args(context))


def endUserInputPerfettoSpan(spanId, metadata=None):
    """End a user input waiting span."""
    _end_pending_span(spanId, metadata)


def emitPerfettoInstant(name, category, args=None):
    """Emit an instant event (marker)."""
    if not isEnabled:
        return
    agentInfo = getCurrentAgentInfo()
    with _state_lock:
        events.append(
            {
                "name": name,
                "cat": category,
                "ph": "i",
                "ts": getTimestamp(),
                "pid": agentInfo["processId"],
                "tid": agentInfo["threadId"],
                "args": _copy_args(args),
            }
        )


def emitPerfettoCounter(name, values):
    """Emit a counter event for tracking metrics over time."""
    if not isEnabled:
        return
    agentInfo = getCurrentAgentInfo()
    with _state_lock:
        events.append(
            {
                "name": name,
                "cat": "counter",
                "ph": "C",
                "ts": getTimestamp(),
                "pid": agentInfo["processId"],
                "tid": agentInfo["threadId"],
                "args": _copy_args(values),
            }
        )


def startInteractionPerfettoSpan(userPrompt=None):
    """Start an interaction span (wraps a full user request cycle)."""
    return _start_pending_span(
        "Interaction",
        "interaction",
        {
            "user_prompt": userPrompt if userPrompt is not None else "",
            "user_prompt_length": len(userPrompt or ""),
        },
    )


def endInteractionPerfettoSpan(spanId):
    """End an interaction span."""
    _end_pending_span(spanId)


def stopWriteInterval():
    """Stop the periodic write timer."""
    global writeIntervalTask, staleSpanCleanupTask
    _cancel_task(writeIntervalTask)
    _cancel_task(staleSpanCleanupTask)
    writeIntervalTask = None
    staleSpanCleanupTask = None


def closeOpenSpans():
    """Force-close any remaining open spans at session end."""
    if not isEnabled:
        return
    endTime = getTimestamp()
    with _state_lock:
        openSpans = list(pendingSpans.values())
        pendingSpans.clear()
        for span in openSpans:
            events.append(
                {
                    "name": span["name"],
                    "cat": span["category"],
                    "ph": "E",
                    "ts": endTime,
                    "pid": span["agentInfo"]["processId"],
                    "tid": span["agentInfo"]["threadId"],
                    "args": {**span["args"], "closed_at_exit": True},
                }
            )


async def periodicWrite():
    """Write the full trace to disk."""
    if not isEnabled:
        return
    try:
        path = _ensure_trace_parent_dir()
        if path is None:
            return
        document = buildTraceDocument()
        await asyncio.to_thread(path.write_text, document, encoding="utf-8")
    except Exception as exc:
        logForDebugging(f"[Perfetto] periodic write failed: {exc}", level="error")


async def writePerfettoTrace():
    """Final async write: close open spans and write the complete trace."""
    global traceWritten
    if not isEnabled or traceWritten:
        return
    closeOpenSpans()
    evictStaleSpans()
    evictOldestEvents()
    path = _ensure_trace_parent_dir()
    if path is None:
        return
    document = buildTraceDocument()
    await asyncio.to_thread(path.write_text, document, encoding="utf-8")
    traceWritten = True


def writePerfettoTraceSync():
    """Final synchronous write (fallback for process exit)."""
    global traceWritten
    if not isEnabled or traceWritten:
        return
    try:
        closeOpenSpans()
        evictStaleSpans()
        evictOldestEvents()
        path = _ensure_trace_parent_dir()
        if path is None:
            return
        path.write_text(buildTraceDocument(), encoding="utf-8")
        traceWritten = True
    except Exception as exc:
        logForDebugging(f"[Perfetto] sync write failed: {exc}", level="error")


def getPerfettoEvents():
    """Get all recorded events (for testing)."""
    with _state_lock:
        return [*metadataEvents, *events]


def resetPerfettoTracer():
    """Reset the tracer state (for testing)."""
    global isEnabled, tracePath, totalAgentCount, startTimeMs, spanIdCounter, traceWritten, processIdCounter
    stopWriteInterval()
    with _state_lock:
        isEnabled = False
        tracePath = None
        metadataEvents.clear()
        events.clear()
        pendingSpans.clear()
        agentRegistry.clear()
        agentIdToProcessId.clear()
        totalAgentCount = 0
        startTimeMs = 0.0
        spanIdCounter = 0
        traceWritten = False
        processIdCounter = 1


async def triggerPeriodicWriteForTesting():
    """Trigger a periodic write immediately (for testing)."""
    await periodicWrite()


def evictStaleSpansForTesting():
    """Evict stale spans immediately (for testing)."""
    evictStaleSpans()


def evictOldestEventsForTesting():
    evictOldestEvents()


string_to_numeric_hash = stringToNumericHash
get_process_id_for_agent = getProcessIdForAgent
get_current_agent_info = getCurrentAgentInfo
get_timestamp = getTimestamp
generate_span_id = generateSpanId
evict_stale_spans = evictStaleSpans
build_trace_document = buildTraceDocument
evict_oldest_events = evictOldestEvents
initialize_perfetto_tracing = initializePerfettoTracing
emit_process_metadata = emitProcessMetadata
is_perfetto_tracing_enabled = isPerfettoTracingEnabled
register_agent = registerAgent
unregister_agent = unregisterAgent
start_llm_request_perfetto_span = startLLMRequestPerfettoSpan
end_llm_request_perfetto_span = endLLMRequestPerfettoSpan
start_tool_perfetto_span = startToolPerfettoSpan
end_tool_perfetto_span = endToolPerfettoSpan
start_user_input_perfetto_span = startUserInputPerfettoSpan
end_user_input_perfetto_span = endUserInputPerfettoSpan
emit_perfetto_instant = emitPerfettoInstant
emit_perfetto_counter = emitPerfettoCounter
start_interaction_perfetto_span = startInteractionPerfettoSpan
end_interaction_perfetto_span = endInteractionPerfettoSpan
stop_write_interval = stopWriteInterval
close_open_spans = closeOpenSpans
write_perfetto_trace = writePerfettoTrace
write_perfetto_trace_sync = writePerfettoTraceSync
get_perfetto_events = getPerfettoEvents
reset_perfetto_tracer = resetPerfettoTracer
trigger_periodic_write_for_testing = triggerPeriodicWriteForTesting
evict_stale_spans_for_testing = evictStaleSpansForTesting
evict_oldest_events_for_testing = evictOldestEventsForTesting


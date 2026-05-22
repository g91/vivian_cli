"""
Port of src/utils/headlessProfiler.ts
"""
from __future__ import annotations

import os
import random
import time
from typing import Any

from ..bootstrap.state import getIsNonInteractiveSession
from ..services.analytics.index import logEvent
from .debug import logForDebugging
from .envUtils import is_env_truthy


DETAILED_PROFILING = is_env_truthy(os.environ.get("vivian_CODE_PROFILE_STARTUP"))
STATSIG_SAMPLE_RATE = 0.05
STATSIG_LOGGING_SAMPLED = os.environ.get("USER_TYPE") == "ant" or random.random() < STATSIG_SAMPLE_RATE
SHOULD_PROFILE = DETAILED_PROFILING or STATSIG_LOGGING_SAMPLED
MARK_PREFIX = "headless_"
_current_turn_number = -1
_marks: list[dict[str, float | str]] = []

def clearHeadlessMarks():
    """Clear all headless profiler marks from performance timeline"""
    global _marks
    _marks = []


def headlessProfilerStartTurn():
    """Start a new turn for profiling. Clears previous marks, increments turn number,
and records turn_start. Call this at the beginning of each user message processing."""
    global _current_turn_number
    if not getIsNonInteractiveSession() or not SHOULD_PROFILE:
        return
    _current_turn_number += 1
    clearHeadlessMarks()
    _marks.append({"name": f"{MARK_PREFIX}turn_start", "startTime": time.perf_counter() * 1000.0})
    if DETAILED_PROFILING:
        logForDebugging(f"[headlessProfiler] Started turn {_current_turn_number}")


def headlessProfilerCheckpoint(name):
    """Record a checkpoint with the given name.
Only records if in headless mode and profiling is enabled."""
    if not name or not getIsNonInteractiveSession() or not SHOULD_PROFILE:
        return
    timestamp = time.perf_counter() * 1000.0
    _marks.append({"name": f"{MARK_PREFIX}{name}", "startTime": timestamp})
    if DETAILED_PROFILING:
        logForDebugging(f"[headlessProfiler] Checkpoint: {name} at {timestamp:.1f}ms")


def logHeadlessProfilerTurn():
    """Log headless latency metrics for the current turn to Statsig.
Call this at the end of each turn (before processing next user message)."""
    if not getIsNonInteractiveSession() or not SHOULD_PROFILE:
        return
    if not _marks:
        return

    checkpoint_times: dict[str, float] = {}
    for mark in _marks:
        checkpoint_times[str(mark["name"])[len(MARK_PREFIX):]] = float(mark["startTime"])

    turn_start = checkpoint_times.get("turn_start")
    if turn_start is None:
        return

    metadata: dict[str, int | str] = {"turn_number": _current_turn_number}
    system_message_time = checkpoint_times.get("system_message_yielded")
    if system_message_time is not None and _current_turn_number == 0:
        metadata["time_to_system_message_ms"] = round(system_message_time)

    query_start_time = checkpoint_times.get("query_started")
    if query_start_time is not None:
        metadata["time_to_query_start_ms"] = round(query_start_time - turn_start)

    first_chunk_time = checkpoint_times.get("first_chunk")
    if first_chunk_time is not None:
        metadata["time_to_first_response_ms"] = round(first_chunk_time - turn_start)

    api_request_time = checkpoint_times.get("api_request_sent")
    if query_start_time is not None and api_request_time is not None:
        metadata["query_overhead_ms"] = round(api_request_time - query_start_time)

    metadata["checkpoint_count"] = len(_marks)
    if os.environ.get("vivian_CODE_ENTRYPOINT"):
        metadata["entrypoint"] = os.environ["vivian_CODE_ENTRYPOINT"]

    if STATSIG_LOGGING_SAMPLED:
        try:
            logEvent("tengu_headless_latency", metadata)
        except Exception:
            pass

    if DETAILED_PROFILING:
        logForDebugging(f"[headlessProfiler] Turn {_current_turn_number} metrics: {metadata}")


clear_headless_marks = clearHeadlessMarks
headless_profiler_start_turn = headlessProfilerStartTurn
headless_profiler_checkpoint = headlessProfilerCheckpoint
log_headless_profiler_turn = logHeadlessProfilerTurn


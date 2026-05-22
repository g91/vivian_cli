"""
Port of src/utils/queryProfiler.ts
"""
from __future__ import annotations

import math
import os
import time
from typing import Any

from .debug import logForDebugging
from .envUtils import is_env_truthy


ENABLED = is_env_truthy(os.environ.get("vivian_CODE_PROFILE_QUERY"))
_marks: list[dict[str, Any]] = []
_query_count = 0


def startQueryProfile():
    """Start profiling a new query session"""
    global _marks, _query_count
    if not ENABLED:
        return
    _marks = []
    _query_count += 1
    queryCheckpoint("query_user_input_received")


def queryCheckpoint(name):
    """Record a checkpoint with the given name"""
    if not ENABLED or not name:
        return
    _marks.append({"name": name, "startTime": time.perf_counter() * 1000.0})


def endQueryProfile():
    """End the current query profiling session"""
    if not ENABLED:
        return
    queryCheckpoint("query_profile_end")


def getSlowWarning(deltaMs, name):
    """Identify slow operations (> 100ms delta)"""
    if name == "query_user_input_received":
        return ""
    if deltaMs > 1000:
        return " WARNING VERY SLOW"
    if deltaMs > 100:
        return " WARNING SLOW"
    if "git_status" in name and deltaMs > 50:
        return " WARNING git status"
    if "tool_schema" in name and deltaMs > 50:
        return " WARNING tool schemas"
    if "client_creation" in name and deltaMs > 50:
        return " WARNING client creation"
    return ""


def getQueryProfileReport():
    """Get a formatted report of all checkpoints for the current/last query"""
    if not ENABLED:
        return "Query profiling not enabled (set vivian_CODE_PROFILE_QUERY=1)"
    if not _marks:
        return "No query profiling checkpoints recorded"

    baseline_time = _marks[0]["startTime"]
    prev_time = baseline_time
    api_request_sent_time = None
    first_chunk_time = None
    lines = ["=" * 80, f"QUERY PROFILING REPORT - Query #{_query_count}", "=" * 80, ""]

    for mark in _marks:
        relative_time = mark["startTime"] - baseline_time
        delta_ms = mark["startTime"] - prev_time
        lines.append(
            f"{relative_time:8.1f}ms (+{delta_ms:7.1f}ms) {mark['name']}{getSlowWarning(delta_ms, mark['name'])}"
        )
        if mark["name"] == "query_api_request_sent":
            api_request_sent_time = relative_time
        if mark["name"] == "query_first_chunk_received":
            first_chunk_time = relative_time
        prev_time = mark["startTime"]

    total_time = _marks[-1]["startTime"] - baseline_time
    lines.extend(["", "-" * 80])
    if first_chunk_time is not None and api_request_sent_time is not None:
        pre_request_overhead = api_request_sent_time
        network_latency = first_chunk_time - api_request_sent_time
        pre_request_percent = (pre_request_overhead / first_chunk_time * 100) if first_chunk_time else 0
        network_percent = (network_latency / first_chunk_time * 100) if first_chunk_time else 0
        lines.append(f"Total TTFT: {first_chunk_time:.1f}ms")
        lines.append(
            f"  - Pre-request overhead: {pre_request_overhead:.1f}ms ({pre_request_percent:.1f}%)"
        )
        lines.append(f"  - Network latency: {network_latency:.1f}ms ({network_percent:.1f}%)")
    else:
        lines.append(f"Total time: {total_time:.1f}ms")

    lines.append(getPhaseSummary(_marks, baseline_time))
    lines.append("=" * 80)
    return "\n".join(lines)


def getPhaseSummary(marks, baselineTime):
    """Get phase-based summary showing time spent in each major phase"""
    phases = [
        ("Context loading", "query_context_loading_start", "query_context_loading_end"),
        ("Microcompact", "query_microcompact_start", "query_microcompact_end"),
        ("Autocompact", "query_autocompact_start", "query_autocompact_end"),
        ("Query setup", "query_setup_start", "query_setup_end"),
        ("Tool schemas", "query_tool_schema_build_start", "query_tool_schema_build_end"),
        ("Message normalization", "query_message_normalization_start", "query_message_normalization_end"),
        ("Client creation", "query_client_creation_start", "query_client_creation_end"),
        ("Network TTFB", "query_api_request_sent", "query_first_chunk_received"),
        ("Tool execution", "query_tool_execution_start", "query_tool_execution_end"),
    ]
    mark_map = {mark["name"]: mark["startTime"] - baselineTime for mark in marks}
    lines = ["", "PHASE BREAKDOWN:"]
    for phase_name, start_name, end_name in phases:
        start_time = mark_map.get(start_name)
        end_time = mark_map.get(end_name)
        if start_time is None or end_time is None:
            continue
        duration = end_time - start_time
        bar = "#" * min(math.ceil(duration / 10), 50)
        lines.append(f"  {phase_name.ljust(22)} {duration:10.1f}ms {bar}")
    api_request_sent = mark_map.get("query_api_request_sent")
    if api_request_sent is not None:
        lines.extend(["", f"  {'Total pre-API overhead'.ljust(22)} {api_request_sent:10.1f}ms"])
    return "\n".join(lines)


def logQueryProfileReport():
    """Log the query profile report to debug output"""
    if not ENABLED:
        return
    logForDebugging(getQueryProfileReport())


start_query_profile = startQueryProfile
query_checkpoint = queryCheckpoint
end_query_profile = endQueryProfile
get_slow_warning = getSlowWarning
get_query_profile_report = getQueryProfileReport
get_phase_summary = getPhaseSummary
log_query_profile_report = logQueryProfileReport


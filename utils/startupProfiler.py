"""Port of src/utils/startupProfiler.ts."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import os
import os.path
import random
import time

from ..bootstrap.state import getSessionId
from ..services.analytics.index import logEvent
from .debug import log_for_debugging
from .envUtils import get_vivian_config_home_dir, is_env_truthy

try:
    import resource
except Exception:
    resource = None


DETAILED_PROFILING = is_env_truthy(os.environ.get("vivian_CODE_PROFILE_STARTUP"))
STATSIG_SAMPLE_RATE = 0.005
STATSIG_LOGGING_SAMPLED = os.environ.get("USER_TYPE") == "ant" or random.random() < STATSIG_SAMPLE_RATE
SHOULD_PROFILE = DETAILED_PROFILING or STATSIG_LOGGING_SAMPLED
PHASE_DEFINITIONS = {
    "import_time": ("cli_entry", "main_tsx_imports_loaded"),
    "init_time": ("init_function_start", "init_function_end"),
    "settings_time": ("eagerLoadSettings_start", "eagerLoadSettings_end"),
    "total_time": ("cli_entry", "main_after_run"),
}
_START_TIME = time.perf_counter()
_MARKS: List[Tuple[str, float]] = []
_MEMORY_SNAPSHOTS: List[Optional[int]] = []
_reported = False


def _now_ms() -> float:
    return (time.perf_counter() - _START_TIME) * 1000.0


def _memory_snapshot() -> Optional[int]:
    if not DETAILED_PROFILING or resource is None:
        return None
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return int(getattr(usage, "ru_maxrss", 0))
    except Exception:
        return None


def _format_ms(value: float) -> str:
    return f"{value:.1f}"


def _format_timeline_line(mark_time: float, delta: float, name: str, memory: Optional[int]) -> str:
    memory_text = f" | rss={memory}KB" if memory is not None else ""
    return f"{_format_ms(mark_time):>8} ms | +{_format_ms(delta):>7} ms | {name}{memory_text}"


def profileCheckpoint(name):
    """Record a checkpoint with the given name"""
    if not SHOULD_PROFILE or name is None:
        return None
    _MARKS.append((name, _now_ms()))
    if DETAILED_PROFILING:
        _MEMORY_SNAPSHOTS.append(_memory_snapshot())
    return None


def getReport():
    """Get a formatted report of all checkpoints"""
    if not DETAILED_PROFILING:
        return "Startup profiling not enabled"
    if not _MARKS:
        return "No profiling checkpoints recorded"

    lines = [
        "=" * 80,
        "STARTUP PROFILING REPORT",
        "=" * 80,
        "",
    ]
    prev_time = 0.0
    for index, (name, mark_time) in enumerate(_MARKS):
        memory = _MEMORY_SNAPSHOTS[index] if index < len(_MEMORY_SNAPSHOTS) else None
        lines.append(_format_timeline_line(mark_time, mark_time - prev_time, name, memory))
        prev_time = mark_time
    lines.append("")
    lines.append(f"Total startup time: {_format_ms(_MARKS[-1][1])}ms")
    lines.append("=" * 80)
    return "\n".join(lines)


def profileReport():
    global _reported
    if _reported:
        return None
    _reported = True

    logStartupPerf()

    if DETAILED_PROFILING:
        path = getStartupPerfLogPath()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        report = getReport()
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(report)
        log_for_debugging("Startup profiling report:")
        log_for_debugging(report)
    return None


def isDetailedProfilingEnabled():
    return DETAILED_PROFILING


def getStartupPerfLogPath():
    return os.path.join(get_vivian_config_home_dir(), "startup-perf", f"{getSessionId()}.txt")


def logStartupPerf():
    """Log startup performance phases to Statsig."""
    if not STATSIG_LOGGING_SAMPLED or not _MARKS:
        return None

    checkpoint_times: Dict[str, float] = {name: mark_time for name, mark_time in _MARKS}
    metadata: Dict[str, int] = {}
    for phase_name, (start_checkpoint, end_checkpoint) in PHASE_DEFINITIONS.items():
        start_time = checkpoint_times.get(start_checkpoint)
        end_time = checkpoint_times.get(end_checkpoint)
        if start_time is not None and end_time is not None:
            metadata[f"{phase_name}_ms"] = round(end_time - start_time)
    metadata["checkpoint_count"] = len(_MARKS)
    logEvent("tengu_startup_perf", metadata)
    return None


if SHOULD_PROFILE:
    profileCheckpoint("profiler_initialized")


profile_checkpoint = profileCheckpoint
get_report = getReport
profile_report = profileReport
is_detailed_profiling_enabled = isDetailedProfilingEnabled
get_startup_perf_log_path = getStartupPerfLogPath
log_startup_perf = logStartupPerf


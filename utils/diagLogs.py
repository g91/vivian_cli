"""
passpass of src/utils/diagLogs
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict
import os
import os.path
import json
import time
from datetime import datetime, timezone


DiagnosticLogLevel = str
DiagnosticLogEntry = Dict[str, Any]


def logForDiagnosticsNoPII(level, event, data=None):
    log_file = getDiagnosticLogFile()
    if not log_file:
        return None

    entry: DiagnosticLogEntry = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "level": level,
        "event": event,
        "data": data or {},
    }
    line = json.dumps(entry, ensure_ascii=True, separators=(",", ":")) + "\n"

    try:
        with open(log_file, "a", encoding="utf-8") as handle:
            handle.write(line)
    except Exception:
        try:
            directory = os.path.dirname(log_file)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(log_file, "a", encoding="utf-8") as handle:
                handle.write(line)
        except Exception:
            pass
    return None


def getDiagnosticLogFile():
    return os.environ.get("vivian_CODE_DIAGNOSTICS_FILE")


async def withDiagnosticsTiming(event, fn=None, getData=None):
    """Wraps an async function with diagnostic timing logs."""
    if fn is None:
        raise TypeError("withDiagnosticsTiming requires an async function")

    start_time = time.time() * 1000
    logForDiagnosticsNoPII("info", f"{event}_started")

    try:
        result = await fn()
        additional_data = getData(result) if getData else {}
        payload = {"duration_ms": int(time.time() * 1000 - start_time), **additional_data}
        logForDiagnosticsNoPII("info", f"{event}_completed", payload)
        return result
    except Exception:
        logForDiagnosticsNoPII(
            "error",
            f"{event}_failed",
            {"duration_ms": int(time.time() * 1000 - start_time)},
        )
        raise


log_for_diagnostics_no_pii = logForDiagnosticsNoPII
get_diagnostic_log_file = getDiagnosticLogFile
with_diagnostics_timing = withDiagnosticsTiming


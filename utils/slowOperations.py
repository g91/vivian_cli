"""Slow-operation wrappers (JSON, clone) — mirrors src/utils/slowOperations.ts"""
from __future__ import annotations

import copy
import json
import os
import time
from typing import Any, Optional

# Threshold in ms for logging slow operations
_SLOW_OPERATION_THRESHOLD_MS = float(
    os.environ.get("vivian_CODE_SLOW_OPERATION_THRESHOLD_MS", "inf") or "inf"
)


def json_parse(text: str) -> Any:
    """Parse JSON string, logging slow operations."""
    start = time.monotonic()
    result = json.loads(text)
    elapsed_ms = (time.monotonic() - start) * 1000
    if elapsed_ms > _SLOW_OPERATION_THRESHOLD_MS:
        from .debug import log_for_debugging
        log_for_debugging(f"[slowOperations] json_parse took {elapsed_ms:.1f}ms ({len(text)} chars)")
    return result


def json_stringify(value: Any, *, indent: Optional[int] = None) -> str:
    """Serialize value to JSON string, logging slow operations."""
    start = time.monotonic()
    result = json.dumps(value, indent=indent, ensure_ascii=False, default=str)
    elapsed_ms = (time.monotonic() - start) * 1000
    if elapsed_ms > _SLOW_OPERATION_THRESHOLD_MS:
        from .debug import log_for_debugging
        log_for_debugging(f"[slowOperations] json_stringify took {elapsed_ms:.1f}ms")
    return result


def clone_deep(value: Any) -> Any:
    """Deep-clone a value using copy.deepcopy, logging slow operations."""
    start = time.monotonic()
    result = copy.deepcopy(value)
    elapsed_ms = (time.monotonic() - start) * 1000
    if elapsed_ms > _SLOW_OPERATION_THRESHOLD_MS:
        from .debug import log_for_debugging
        log_for_debugging(f"[slowOperations] clone_deep took {elapsed_ms:.1f}ms")
    return result


def slow_logging(label: str, fn, *args, **kwargs):
    """Run fn(*args, **kwargs) and log if it exceeds the slow threshold."""
    start = time.monotonic()
    result = fn(*args, **kwargs)
    elapsed_ms = (time.monotonic() - start) * 1000
    if elapsed_ms > _SLOW_OPERATION_THRESHOLD_MS:
        from .debug import log_for_debugging
        log_for_debugging(f"[slowOperations] {label} took {elapsed_ms:.1f}ms")
    return result


jsonParse = json_parse
jsonStringify = json_stringify
cloneDeep = clone_deep
slowLogging = slow_logging

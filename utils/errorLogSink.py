"""Error log sink implementation — partial port of src/utils/errorLogSink.ts."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ..bootstrap.state import getSessionId
from .cachePaths import CACHE_PATHS
from .cleanupRegistry import register_cleanup
from .debug import logForDebugging
from .log import attachErrorLogSink, dateToFilename


DATE = dateToFilename(datetime.utcnow())


@dataclass
class _JsonlWriter:
    path: str
    buffer: list[str] = field(default_factory=list)

    def write(self, obj: object) -> None:
        self.buffer.append(json.dumps(obj, ensure_ascii=False) + "\n")
        if len(self.buffer) >= 50:
            self.flush()

    def flush(self) -> None:
        if not self.buffer:
            return
        path = Path(self.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("".join(self.buffer))
        self.buffer.clear()

    def dispose(self) -> None:
        self.flush()


JsonlWriter = _JsonlWriter
_log_writers: dict[str, JsonlWriter] = {}


def getErrorsPath() -> str:
    """Gets the path to the errors log file."""
    return str(Path(CACHE_PATHS.errors()) / f"{DATE}.jsonl")


def getMCPLogsPath(serverName: str) -> str:
    """Gets the path to MCP logs for a server."""
    return str(Path(CACHE_PATHS.mcp_logs(serverName)) / f"{DATE}.jsonl")


def createJsonlWriter(options: dict[str, Any] | None = None) -> JsonlWriter:
    path = (options or {}).get("path")
    if not path:
        raise ValueError("createJsonlWriter requires a path option")
    return JsonlWriter(path=str(path))


def _flushLogWritersForTesting() -> None:
    """Flush all buffered log writers. Used for testing."""
    for writer in _log_writers.values():
        writer.flush()


def _clearLogWritersForTesting() -> None:
    """Clear all buffered log writers. Used for testing."""
    for writer in _log_writers.values():
        writer.dispose()
    _log_writers.clear()


def getLogWriter(path: str) -> JsonlWriter:
    writer = _log_writers.get(path)
    if writer is None:
        writer = createJsonlWriter({"path": path})
        _log_writers[path] = writer

        async def _cleanup() -> None:
            writer.dispose()

        register_cleanup(_cleanup)
    return writer


def appendToLog(path: str, message: dict[str, Any]) -> None:
    if os.environ.get("USER_TYPE") != "ant":
        return
    message_with_timestamp = {
        "timestamp": datetime.utcnow().isoformat(),
        **message,
        "cwd": os.getcwd(),
        "userType": os.environ.get("USER_TYPE"),
        "sessionId": getSessionId(),
    }
    getLogWriter(path).write(message_with_timestamp)


def extractServerMessage(data: Any) -> str | None:
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        if isinstance(data.get("message"), str):
            return data["message"]
        error = data.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
    return None


def logErrorImpl(error: Exception) -> None:
    """Implementation for logError - writes error to debug log and file."""
    error_str = "".join(__import__("traceback").format_exception(type(error), error, error.__traceback__)) if error.__traceback__ else str(error)
    logForDebugging(f"{type(error).__name__}: {error_str}", level="error")
    appendToLog(getErrorsPath(), {"error": error_str})


def logMCPErrorImpl(serverName: str, error: object) -> None:
    """Implementation for logMCPError - writes MCP error to debug log and file."""
    logForDebugging(f'MCP server "{serverName}" {error}', level="error")
    error_str = str(error)
    getLogWriter(getMCPLogsPath(serverName)).write(
        {
            "error": error_str,
            "timestamp": datetime.utcnow().isoformat(),
            "sessionId": getSessionId(),
            "cwd": os.getcwd(),
        }
    )


def logMCPDebugImpl(serverName: str, message: str) -> None:
    """Implementation for logMCPDebug - writes MCP debug message to log file."""
    logForDebugging(f'MCP server "{serverName}": {message}')
    getLogWriter(getMCPLogsPath(serverName)).write(
        {
            "debug": message,
            "timestamp": datetime.utcnow().isoformat(),
            "sessionId": getSessionId(),
            "cwd": os.getcwd(),
        }
    )


def initializeErrorLogSink() -> None:
    """Initialize the error log sink."""
    attachErrorLogSink(
        {
            "logError": logErrorImpl,
            "logMCPError": logMCPErrorImpl,
            "logMCPDebug": logMCPDebugImpl,
            "getErrorsPath": getErrorsPath,
            "getMCPLogsPath": getMCPLogsPath,
        }
    )
    logForDebugging("Error log sink initialized")


get_errors_path = getErrorsPath
get_mcp_logs_path = getMCPLogsPath
create_jsonl_writer = createJsonlWriter
flush_log_writers_for_testing = _flushLogWritersForTesting
clear_log_writers_for_testing = _clearLogWritersForTesting
get_log_writer = getLogWriter
append_to_log = appendToLog
extract_server_message = extractServerMessage
log_error_impl = logErrorImpl
log_mcp_error_impl = logMCPErrorImpl
log_mcp_debug_impl = logMCPDebugImpl
initialize_error_log_sink = initializeErrorLogSink


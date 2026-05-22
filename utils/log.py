"""Logging helpers — partial port of src/utils/log.ts."""
from __future__ import annotations

import json
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from ..bootstrap.state import setLastAPIRequest, setLastAPIRequestMessages
from ..constants.tools import TICK_TAG
from ..types.logs import LogOption, sortLogs
from .cachePaths import CACHE_PATHS
from .displayTags import strip_display_tags, strip_display_tags_allow_empty
from .envUtils import is_env_truthy
from .errors import to_error
from .privacyLevel import isEssentialTrafficOnly


ErrorLogSink = dict[str, Any]
QueuedErrorEvent = dict[str, Any]

MAX_IN_MEMORY_ERRORS = 100
_in_memory_error_log: list[dict[str, str]] = []
_error_queue: list[QueuedErrorEvent] = []
_error_log_sink: ErrorLogSink | None = None


def getLogDisplayTitle(log: dict[str, Any], defaultTitle: str | None = None) -> str:
    """Return the best display title for a log/session."""
    first_prompt = log.get("firstPrompt") or ""
    is_autonomous_prompt = first_prompt.startswith(f"<{TICK_TAG}>")
    stripped_first_prompt = (
        strip_display_tags_allow_empty(first_prompt) if first_prompt else ""
    )
    use_first_prompt = bool(stripped_first_prompt) and not is_autonomous_prompt
    title = (
        log.get("agentName")
        or log.get("customTitle")
        or log.get("summary")
        or (stripped_first_prompt if use_first_prompt else None)
        or defaultTitle
        or ("Autonomous session" if is_autonomous_prompt else None)
        or ((log.get("sessionId") or "")[:8] if log.get("sessionId") else "")
        or ""
    )
    return strip_display_tags(str(title)).strip()


def dateToFilename(date: datetime) -> str:
    return date.isoformat().replace(":", "-").replace(".", "-")


def addToInMemoryErrorLog(errorInfo: dict[str, str]) -> None:
    if len(_in_memory_error_log) >= MAX_IN_MEMORY_ERRORS:
        _in_memory_error_log.pop(0)
    _in_memory_error_log.append(errorInfo)


def attachErrorLogSink(newSink: ErrorLogSink) -> None:
    """Attach the error sink and drain queued events once."""
    global _error_log_sink
    if _error_log_sink is not None:
        return
    _error_log_sink = newSink
    if not _error_queue:
        return
    queued_events = list(_error_queue)
    _error_queue.clear()
    for event in queued_events:
        if event["type"] == "error":
            _error_log_sink["logError"](event["error"])
        elif event["type"] == "mcpError":
            _error_log_sink["logMCPError"](event["serverName"], event["error"])
        elif event["type"] == "mcpDebug":
            _error_log_sink["logMCPDebug"](event["serverName"], event["message"])


def _should_skip_error_reporting() -> bool:
    return (
        is_env_truthy(os.environ.get("vivian_CODE_USE_BEDROCK"))
        or is_env_truthy(os.environ.get("vivian_CODE_USE_VERTEX"))
        or is_env_truthy(os.environ.get("vivian_CODE_USE_FOUNDRY"))
        or bool(os.environ.get("DISABLE_ERROR_REPORTING"))
        or isEssentialTrafficOnly()
    )


def logError(error: object, maybe_error: Exception | None = None) -> None:
    """Record an error to memory and optionally forward to the attached sink."""
    if _should_skip_error_reporting():
        return
    err = to_error(maybe_error) if maybe_error is not None else to_error(error)
    if maybe_error is not None and error:
        err = Exception(f"{error}: {err}")
    try:
        error_str = (
            "".join(traceback.format_exception(type(err), err, err.__traceback__))
            if err.__traceback__
            else str(err)
        )
        error_info = {"error": error_str, "timestamp": datetime.utcnow().isoformat()}
        addToInMemoryErrorLog(error_info)
        if _error_log_sink is None:
            _error_queue.append({"type": "error", "error": err})
            return
        _error_log_sink["logError"](err)
    except Exception:
        return


def getInMemoryErrors() -> list[dict[str, str]]:
    return list(_in_memory_error_log)


def loadErrorLogs() -> list[LogOption]:
    """Load persisted error logs sorted by date."""
    return _load_log_list_sync(CACHE_PATHS.errors())


async def getErrorLogByIndex(index: int) -> LogOption | None:
    logs = loadErrorLogs()
    return logs[index] if 0 <= index < len(logs) else None


async def loadLogList(path: str) -> list[LogOption]:
    return _load_log_list_sync(path)


def _read_jsonl_messages(full_path: Path) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    try:
        with open(full_path, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except Exception:
                    continue
                if isinstance(parsed, dict):
                    messages.append(parsed)
    except Exception:
        return []
    return messages


def _load_log_list_sync(path: str) -> list[LogOption]:
    base_path = Path(path)
    try:
        files = [entry for entry in base_path.iterdir() if entry.is_file()]
    except Exception:
        logError(Exception(f"No logs found at {path}"))
        return []

    log_data: list[LogOption] = []
    for index, file_path in enumerate(files):
        messages = _read_jsonl_messages(file_path)
        if not messages:
            continue
        first_message = messages[0]
        last_message = messages[-1]
        file_stats = file_path.stat()
        first_prompt = "No prompt"
        if first_message.get("type") == "user":
            message_obj = first_message.get("message")
            if isinstance(message_obj, dict) and isinstance(message_obj.get("content"), str):
                first_prompt = message_obj["content"]
            elif isinstance(message_obj, str):
                first_prompt = message_obj

        date = dateToFilename(datetime.fromtimestamp(file_stats.st_mtime))
        created = parseISOString(str(first_message.get("timestamp") or date))
        modified = parseISOString(str(last_message.get("timestamp") or date))
        prompt_summary = (first_prompt.split("\n")[0][:50] + ("..." if len(first_prompt) > 50 else "")) or "No prompt"
        log_data.append(
            LogOption(
                date=date,
                fullPath=str(file_path),
                messages=messages,  # type: ignore[arg-type]
                value=index,
                created=created,
                modified=modified,
                firstPrompt=prompt_summary,
                messageCount=len(messages),
                isSidechain="sidechain" in str(file_path),
            )
        )

    return [
        LogOption(**{**log.__dict__, "value": index})
        for index, log in enumerate(sortLogs(log_data))
    ]


def parseISOString(s: str) -> datetime:
    parts = [part for part in __import__("re").split(r"\D+", s) if part]
    if len(parts) >= 6:
        year, month, day, hour, minute, second = [int(part) for part in parts[:6]]
        microsecond = int(parts[6].ljust(6, "0")[:6]) if len(parts) > 6 else 0
        return datetime(year, month, day, hour, minute, second, microsecond)
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def logMCPError(serverName: str, error: object) -> None:
    try:
        if _error_log_sink is None:
            _error_queue.append(
                {"type": "mcpError", "serverName": serverName, "error": error}
            )
            return
        _error_log_sink["logMCPError"](serverName, error)
    except Exception:
        return


def logMCPDebug(serverName: str, message: str) -> None:
    try:
        if _error_log_sink is None:
            _error_queue.append(
                {"type": "mcpDebug", "serverName": serverName, "message": message}
            )
            return
        _error_log_sink["logMCPDebug"](serverName, message)
    except Exception:
        return


def captureAPIRequest(params: dict[str, Any], querySource: str | None = None) -> None:
    if not querySource or not querySource.startswith("repl_main_thread"):
        return
    params_without_messages = dict(params)
    messages = params_without_messages.pop("messages", None)
    setLastAPIRequest(params_without_messages)
    setLastAPIRequestMessages(messages if os.environ.get("USER_TYPE") == "ant" else None)


def _resetErrorLogForTesting() -> None:
    global _error_log_sink
    _error_log_sink = None
    _error_queue.clear()
    _in_memory_error_log.clear()


get_log_display_title = getLogDisplayTitle
date_to_filename = dateToFilename
add_to_in_memory_error_log = addToInMemoryErrorLog
attach_error_log_sink = attachErrorLogSink
log_error = logError
get_in_memory_errors = getInMemoryErrors
load_error_logs = loadErrorLogs
get_error_log_by_index = getErrorLogByIndex
load_log_list = loadLogList
parse_iso_string = parseISOString
log_mcp_error = logMCPError
log_mcp_debug = logMCPDebug
capture_api_request = captureAPIRequest
reset_error_log_for_testing = _resetErrorLogForTesting


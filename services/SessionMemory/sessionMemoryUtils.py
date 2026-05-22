"""Session memory utilities — mirrors src/services/SessionMemory/sessionMemoryUtils.ts."""
from __future__ import annotations

import asyncio
import os
import time
from typing import Optional

EXTRACTION_WAIT_TIMEOUT_MS = 15000
EXTRACTION_STALE_THRESHOLD_MS = 60000

DEFAULT_SESSION_MEMORY_CONFIG: dict = {
    "minimumMessageTokensToInit": 10000,
    "minimumTokensBetweenUpdate": 5000,
    "toolCallsBetweenUpdates": 3,
}

SessionMemoryConfig = dict

_session_memory_config: SessionMemoryConfig = dict(DEFAULT_SESSION_MEMORY_CONFIG)
_last_summarized_message_id: Optional[str] = None
_extraction_started_at: Optional[float] = None
_tokens_at_last_extraction: int = 0
_session_memory_initialized: bool = False


def getLastSummarizedMessageId() -> Optional[str]:
    """Get the message ID up to which the session memory is current.

    Mirrors getLastSummarizedMessageId() from sessionMemoryUtils.ts.
    """
    return _last_summarized_message_id


def setLastSummarizedMessageId(message_id: Optional[str]) -> None:
    """Set the last summarized message ID.

    Mirrors setLastSummarizedMessageId() from sessionMemoryUtils.ts.
    """
    global _last_summarized_message_id
    _last_summarized_message_id = message_id


def markExtractionStarted() -> None:
    """Mark extraction as started."""
    global _extraction_started_at
    _extraction_started_at = time.time() * 1000


def markExtractionCompleted() -> None:
    """Mark extraction as completed."""
    global _extraction_started_at
    _extraction_started_at = None


async def waitForSessionMemoryExtraction() -> None:
    """Wait for any in-progress session memory extraction to complete (15s timeout).

    Mirrors waitForSessionMemoryExtraction() from sessionMemoryUtils.ts.
    """
    start_time = time.time() * 1000
    while _extraction_started_at is not None:
        extraction_age = (time.time() * 1000) - _extraction_started_at
        if extraction_age > EXTRACTION_STALE_THRESHOLD_MS:
            return
        if (time.time() * 1000) - start_time > EXTRACTION_WAIT_TIMEOUT_MS:
            return
        await asyncio.sleep(1.0)


async def getSessionMemoryContent() -> Optional[str]:
    """Get the current session memory content.

    Mirrors getSessionMemoryContent() from sessionMemoryUtils.ts.
    """
    try:
        from ...utils.permissions.filesystem import get_session_memory_path
        memory_path = get_session_memory_path()
        with open(memory_path, encoding="utf-8") as f:
            content = f.read()
        try:
            from ..analytics.index import logEvent
            logEvent("tengu_session_memory_loaded", {"content_length": len(content)})
        except Exception:
            pass
        return content
    except FileNotFoundError:
        return None
    except Exception:
        return None


def setSessionMemoryConfig(config: dict) -> None:
    """Set the current session memory configuration.

    Mirrors setSessionMemoryConfig() from sessionMemoryUtils.ts.
    """
    _session_memory_config.update(config)


def getSessionMemoryConfig() -> SessionMemoryConfig:
    """Get the current session memory configuration.

    Mirrors getSessionMemoryConfig() from sessionMemoryUtils.ts.
    """
    return dict(_session_memory_config)


def recordExtractionTokenCount(current_token_count: int) -> None:
    """Record the context size at the time of extraction."""
    global _tokens_at_last_extraction
    _tokens_at_last_extraction = current_token_count


def isSessionMemoryInitialized() -> bool:
    """Check if session memory has been initialized."""
    return _session_memory_initialized


def markSessionMemoryInitialized() -> None:
    """Mark session memory as initialized."""
    global _session_memory_initialized
    _session_memory_initialized = True


def hasMetInitializationThreshold(current_token_count: int) -> bool:
    """Check if we've met the threshold to initialize session memory."""
    return current_token_count >= _session_memory_config["minimumMessageTokensToInit"]


def hasMetUpdateThreshold(current_token_count: int) -> bool:
    """Check if we've met the threshold for the next update."""
    tokens_since_last = current_token_count - _tokens_at_last_extraction
    return tokens_since_last >= _session_memory_config["minimumTokensBetweenUpdate"]


def getToolCallsBetweenUpdates() -> int:
    """Get the configured number of tool calls between updates."""
    return _session_memory_config["toolCallsBetweenUpdates"]


def resetSessionMemoryState() -> None:
    """Reset session memory state (useful for testing)."""
    global _session_memory_config, _tokens_at_last_extraction, _session_memory_initialized
    global _last_summarized_message_id, _extraction_started_at
    _session_memory_config = dict(DEFAULT_SESSION_MEMORY_CONFIG)
    _tokens_at_last_extraction = 0
    _session_memory_initialized = False
    _last_summarized_message_id = None
    _extraction_started_at = None


get_last_summarized_message_id = getLastSummarizedMessageId
set_last_summarized_message_id = setLastSummarizedMessageId
mark_extraction_started = markExtractionStarted
mark_extraction_completed = markExtractionCompleted
wait_for_session_memory_extraction = waitForSessionMemoryExtraction
get_session_memory_content = getSessionMemoryContent
set_session_memory_config = setSessionMemoryConfig
get_session_memory_config = getSessionMemoryConfig
record_extraction_token_count = recordExtractionTokenCount
is_session_memory_initialized = isSessionMemoryInitialized
mark_session_memory_initialized = markSessionMemoryInitialized
has_met_initialization_threshold = hasMetInitializationThreshold
has_met_update_threshold = hasMetUpdateThreshold
get_tool_calls_between_updates = getToolCallsBetweenUpdates
reset_session_memory_state = resetSessionMemoryState

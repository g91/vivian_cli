"""Session memory package — mirrors src/services/SessionMemory/."""
from __future__ import annotations

from .sessionMemoryUtils import (
    getLastSummarizedMessageId,
    setLastSummarizedMessageId,
    markExtractionStarted,
    markExtractionCompleted,
    waitForSessionMemoryExtraction,
    getSessionMemoryContent,
    setSessionMemoryConfig,
    getSessionMemoryConfig,
    recordExtractionTokenCount,
    isSessionMemoryInitialized,
    markSessionMemoryInitialized,
    hasMetInitializationThreshold,
    hasMetUpdateThreshold,
    getToolCallsBetweenUpdates,
    resetSessionMemoryState,
    DEFAULT_SESSION_MEMORY_CONFIG,
)

__all__ = [
    "getLastSummarizedMessageId",
    "setLastSummarizedMessageId",
    "markExtractionStarted",
    "markExtractionCompleted",
    "waitForSessionMemoryExtraction",
    "getSessionMemoryContent",
    "setSessionMemoryConfig",
    "getSessionMemoryConfig",
    "recordExtractionTokenCount",
    "isSessionMemoryInitialized",
    "markSessionMemoryInitialized",
    "hasMetInitializationThreshold",
    "hasMetUpdateThreshold",
    "getToolCallsBetweenUpdates",
    "resetSessionMemoryState",
    "DEFAULT_SESSION_MEMORY_CONFIG",
]

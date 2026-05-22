"""Services package — mirrors src/services/."""
from __future__ import annotations

from .analytics import logEvent, logEventAsync, attachAnalyticsSink
from .vivianAiLimits import (
    extractQuotaStatusFromHeaders,
    extractQuotaStatusFromError,
    checkQuotaStatus,
    getRateLimitDisplayName,
)
from .rateLimitMessages import (
    getRateLimitMessage,
    getRateLimitErrorMessage,
    getRateLimitWarning,
    isRateLimitErrorMessage,
)
from .tokenEstimation import (
    roughTokenCountEstimation,
    roughTokenCountEstimationForMessage,
    roughTokenCountEstimationForMessages,
    countTokensWithAPI,
)
from .api import getAnthropicClient, queryModelWithoutStreaming
from .mcp import normalizeNameForMCP, buildMcpToolName, mcpInfoFromString

__all__ = [
    "logEvent",
    "logEventAsync",
    "attachAnalyticsSink",
    "extractQuotaStatusFromHeaders",
    "extractQuotaStatusFromError",
    "checkQuotaStatus",
    "getRateLimitDisplayName",
    "getRateLimitMessage",
    "getRateLimitErrorMessage",
    "getRateLimitWarning",
    "isRateLimitErrorMessage",
    "roughTokenCountEstimation",
    "roughTokenCountEstimationForMessage",
    "roughTokenCountEstimationForMessages",
    "countTokensWithAPI",
    "getAnthropicClient",
    "queryModelWithoutStreaming",
    "normalizeNameForMCP",
    "buildMcpToolName",
    "mcpInfoFromString",
]

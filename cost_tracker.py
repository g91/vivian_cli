"""Cost tracker — mirrors src/cost-tracker.ts."""

from __future__ import annotations

import time
import logging
from typing import Any, Optional

from .bootstrap.state import (
    addToTotalLinesChanged,
    getModelUsage,
    getSessionId,
    getTotalAPIDuration,
    getTotalAPIDurationWithoutRetries,
    getTotalCacheCreationInputTokens,
    getTotalCacheReadInputTokens,
    getTotalCostUSD,
    getTotalDuration,
    getTotalInputTokens,
    getTotalLinesAdded,
    getTotalLinesRemoved,
    getTotalToolDuration,
    getTotalOutputTokens,
    getTotalWebSearchRequests,
    getUsageForModel,
    hasUnknownModelCost,
    resetCostState,
    resetStateForTests,
    setCostStateForRestore,
    setHasUnknownModelCost,
)
from .types import CostState

logger = logging.getLogger(__name__)

_SESSION_COST_STORE: dict[str, dict[str, Any]] = {}


class CostTracker:
    """Tracks session costs, token usage, and code changes."""

    def __init__(self):
        self.total_cost_usd: float = 0.0
        self.total_api_duration: float = 0.0
        self.total_api_duration_without_retries: float = 0.0
        self.total_tool_duration: float = 0.0
        self.total_duration: float = 0.0
        self.total_lines_added: int = 0
        self.total_lines_removed: int = 0
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_cache_read_tokens: int = 0
        self.total_cache_creation_tokens: int = 0
        self.total_web_search_requests: int = 0
        self.model_usage: dict[str, dict[str, Any]] = {}
        self.has_unknown_model_cost: bool = False
        self._session_start: float = time.time()

    def add_usage(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_creation_tokens: int = 0,
        web_search_requests: int = 0,
        cost_usd: float = 0.0,
        model: str = "unknown",
        api_duration_ms: float = 0.0,
    ):
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cache_read_tokens += cache_read_tokens
        self.total_cache_creation_tokens += cache_creation_tokens
        self.total_web_search_requests += web_search_requests
        self.total_cost_usd += cost_usd
        self.total_api_duration += api_duration_ms

        if model not in self.model_usage:
            self.model_usage[model] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_tokens": 0,
                "cache_creation_tokens": 0,
                "web_search_requests": 0,
                "cost_usd": 0.0,
            }
        m = self.model_usage[model]
        m["input_tokens"] += input_tokens
        m["output_tokens"] += output_tokens
        m["cache_read_tokens"] += cache_read_tokens
        m["cache_creation_tokens"] += cache_creation_tokens
        m["web_search_requests"] += web_search_requests
        m["cost_usd"] += cost_usd

    def add_lines_changed(self, added: int = 0, removed: int = 0):
        self.total_lines_added += added
        self.total_lines_removed += removed

    def add_tool_duration(self, duration_ms: float):
        self.total_tool_duration += duration_ms

    @property
    def total_duration_seconds(self) -> float:
        return time.time() - self._session_start

    def get_state(self) -> CostState:
        return CostState(
            total_cost_usd=self.total_cost_usd,
            total_api_duration=self.total_api_duration,
            total_tool_duration=self.total_tool_duration,
            total_lines_added=self.total_lines_added,
            total_lines_removed=self.total_lines_removed,
            total_input_tokens=self.total_input_tokens,
            total_output_tokens=self.total_output_tokens,
            total_cache_read_tokens=self.total_cache_read_tokens,
            total_cache_creation_tokens=self.total_cache_creation_tokens,
            total_web_search_requests=self.total_web_search_requests,
            model_usage=dict(self.model_usage),
            has_unknown_model_cost=self.has_unknown_model_cost,
        )

    def restore_state(self, state: CostState):
        self.total_cost_usd = state.total_cost_usd
        self.total_api_duration = state.total_api_duration
        self.total_tool_duration = state.total_tool_duration
        self.total_lines_added = state.total_lines_added
        self.total_lines_removed = state.total_lines_removed
        self.total_input_tokens = state.total_input_tokens
        self.total_output_tokens = state.total_output_tokens
        self.total_cache_read_tokens = state.total_cache_read_tokens
        self.total_cache_creation_tokens = state.total_cache_creation_tokens
        self.total_web_search_requests = state.total_web_search_requests
        self.model_usage = dict(state.model_usage)
        self.has_unknown_model_cost = state.has_unknown_model_cost

    def reset(self):
        self.__init__()

    def format_total_cost(self) -> str:
        lines = [
            f"Total cost:            ${self.total_cost_usd:.4f}",
            f"Total duration (API):  {self._format_ms(self.total_api_duration)}",
            f"Total duration (wall): {self._format_ms(self.total_duration_seconds * 1000)}",
            f"Total code changes:    {self.total_lines_added} lines added, {self.total_lines_removed} lines removed",
            f"Total tokens:          {self.total_input_tokens} input, {self.total_output_tokens} output",
        ]

        if self.total_cache_read_tokens or self.total_cache_creation_tokens:
            lines.append(
                f"Cache:                 {self.total_cache_read_tokens} read, {self.total_cache_creation_tokens} write"
            )

        if self.model_usage:
            lines.append("Usage by model:")
            for model, usage in self.model_usage.items():
                input_tokens = usage.get("input_tokens", usage.get("inputTokens", 0))
                output_tokens = usage.get("output_tokens", usage.get("outputTokens", 0))
                cost_usd = usage.get("cost_usd", usage.get("costUSD", 0.0))
                lines.append(
                    f"  {model}: {input_tokens} input, "
                    f"{output_tokens} output "
                    f"(${cost_usd:.4f})"
                )

        return "\n".join(lines)

    @staticmethod
    def _format_ms(ms: float) -> str:
        if ms < 1000:
            return f"{ms:.0f}ms"
        elif ms < 60000:
            return f"{ms / 1000:.1f}s"
        else:
            return f"{ms / 60000:.1f}m"


def formatCost(cost: float, maxDecimalPlaces: int = 4) -> str:
    if cost > 0.5:
        return f"${cost:.2f}"
    return f"${cost:.{maxDecimalPlaces}f}"


def getStoredSessionCosts(sessionId: str) -> Optional[dict[str, Any]]:
    return _SESSION_COST_STORE.get(sessionId)


def restoreCostStateForSession(sessionId: str) -> bool:
    data = getStoredSessionCosts(sessionId)
    if not data:
        return False
    setCostStateForRestore(
        total_cost_usd=data.get("totalCostUSD", 0.0),
        total_api_duration=data.get("totalAPIDuration", 0),
        total_api_duration_without_retries=data.get("totalAPIDurationWithoutRetries", 0),
        total_tool_duration=data.get("totalToolDuration", 0),
        total_lines_added=data.get("totalLinesAdded", 0),
        total_lines_removed=data.get("totalLinesRemoved", 0),
        last_duration=data.get("lastDuration"),
        model_usage=data.get("modelUsage"),
    )
    return True


def saveCurrentSessionCosts(fpsMetrics: Optional[Any] = None) -> None:
    session_id = str(getSessionId())
    _SESSION_COST_STORE[session_id] = {
        "totalCostUSD": getTotalCostUSD(),
        "totalAPIDuration": getTotalAPIDuration(),
        "totalAPIDurationWithoutRetries": getTotalAPIDurationWithoutRetries(),
        "totalToolDuration": getTotalToolDuration(),
        "lastDuration": getTotalDuration(),
        "totalLinesAdded": getTotalLinesAdded(),
        "totalLinesRemoved": getTotalLinesRemoved(),
        "lastTotalInputTokens": getTotalInputTokens(),
        "lastTotalOutputTokens": getTotalOutputTokens(),
        "lastTotalCacheCreationInputTokens": getTotalCacheCreationInputTokens(),
        "lastTotalCacheReadInputTokens": getTotalCacheReadInputTokens(),
        "lastTotalWebSearchRequests": getTotalWebSearchRequests(),
        "lastFpsAverage": getattr(fpsMetrics, "averageFps", None) if fpsMetrics is not None else None,
        "lastFpsLow1Pct": getattr(fpsMetrics, "low1PctFps", None) if fpsMetrics is not None else None,
        "modelUsage": dict(getModelUsage()),
        "lastSessionId": session_id,
    }


def formatTotalCost() -> str:
    tracker = CostTracker()
    tracker.total_cost_usd = getTotalCostUSD()
    tracker.total_api_duration = getTotalAPIDuration()
    tracker.total_api_duration_without_retries = getTotalAPIDurationWithoutRetries()
    tracker.total_tool_duration = getTotalToolDuration()
    tracker.total_lines_added = getTotalLinesAdded()
    tracker.total_lines_removed = getTotalLinesRemoved()
    tracker.total_input_tokens = getTotalInputTokens()
    tracker.total_output_tokens = getTotalOutputTokens()
    tracker.total_cache_read_tokens = getTotalCacheReadInputTokens()
    tracker.total_cache_creation_tokens = getTotalCacheCreationInputTokens()
    tracker.total_web_search_requests = getTotalWebSearchRequests()
    tracker.model_usage = dict(getModelUsage())
    tracker.has_unknown_model_cost = hasUnknownModelCost()
    return tracker.format_total_cost()


getTotalCost = getTotalCostUSD
format_cost = formatCost
get_stored_session_costs = getStoredSessionCosts
restore_cost_state_for_session = restoreCostStateForSession
save_current_session_costs = saveCurrentSessionCosts
format_total_cost = formatTotalCost

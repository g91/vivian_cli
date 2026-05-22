"""Token budget tracking — mirrors src/query/tokenBudget.ts.

Tracks continuation counts and token deltas across a multi-turn conversation
to decide when to stop requesting more output (STOP) vs continue (CONTINUE).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal, Union

COMPLETION_THRESHOLD: float = 0.9
DIMINISHING_THRESHOLD: int = 500


@dataclass
class BudgetTracker:
    continuationCount: int = 0
    lastDeltaTokens: int = 0
    lastGlobalTurnTokens: int = 0
    startedAt: float = field(default_factory=time.time)


def createBudgetTracker() -> BudgetTracker:
    """Create a fresh BudgetTracker for a new conversation turn."""
    return BudgetTracker()


@dataclass
class ContinueDecision:
    type: Literal["continue"] = "continue"
    reason: str = ""


@dataclass
class StopDecision:
    type: Literal["stop"] = "stop"
    reason: str = ""


TokenBudgetDecision = Union[ContinueDecision, StopDecision]


def checkTokenBudget(
    tracker: BudgetTracker,
    agentId: str,
    budget: int,
    globalTurnTokens: int,
) -> TokenBudgetDecision:
    """Decide whether to continue or stop based on remaining token budget.

    Returns STOP if:
    - We're above COMPLETION_THRESHOLD of the budget AND token delta is
      diminishing (< DIMINISHING_THRESHOLD new tokens this turn)
    - globalTurnTokens have not increased since last check (model stalled)
    """
    delta = globalTurnTokens - tracker.lastGlobalTurnTokens
    tracker.lastDeltaTokens = delta
    tracker.lastGlobalTurnTokens = globalTurnTokens
    tracker.continuationCount += 1

    if budget <= 0:
        return ContinueDecision(reason="no_budget_set")

    usage_ratio = globalTurnTokens / budget
    if usage_ratio < COMPLETION_THRESHOLD:
        return ContinueDecision(reason=f"usage_ratio={usage_ratio:.2f}")

    if delta < DIMINISHING_THRESHOLD:
        return StopDecision(
            reason=f"diminishing_returns delta={delta} ratio={usage_ratio:.2f}"
        )

    return ContinueDecision(reason=f"above_threshold_but_growing delta={delta}")

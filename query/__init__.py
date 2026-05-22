"""Query package — mirrors src/query/."""
from .config import QueryConfig, QueryGates, buildQueryConfig
from .deps import QueryDeps, productionDeps
from .token_budget import (
    BudgetTracker, ContinueDecision, StopDecision, TokenBudgetDecision,
    createBudgetTracker, checkTokenBudget,
    COMPLETION_THRESHOLD, DIMINISHING_THRESHOLD,
)
from .stop_hooks import StopHookResult, handleStopHooks, collectStopHookResult

__all__ = [
    "QueryConfig", "QueryGates", "buildQueryConfig",
    "QueryDeps", "productionDeps",
    "BudgetTracker", "ContinueDecision", "StopDecision", "TokenBudgetDecision",
    "createBudgetTracker", "checkTokenBudget",
    "COMPLETION_THRESHOLD", "DIMINISHING_THRESHOLD",
    "StopHookResult", "handleStopHooks", "collectStopHookResult",
]

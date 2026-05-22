"""Snake-case compatibility wrapper for permissive policy limits."""
from __future__ import annotations

from .policyLimits import (
    get_restrictions_from_cache,
    isPolicyAllowed,
    is_policy_allowed,
    loadPolicyLimits,
    refreshPolicyLimits,
    waitForPolicyLimitsToLoad,
    wait_for_policy_limits_to_load,
)

__all__ = [
    "get_restrictions_from_cache",
    "isPolicyAllowed",
    "is_policy_allowed",
    "loadPolicyLimits",
    "refreshPolicyLimits",
    "waitForPolicyLimitsToLoad",
    "wait_for_policy_limits_to_load",
]

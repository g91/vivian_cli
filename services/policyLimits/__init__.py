"""Policy limits service package — mirrors src/services/policyLimits/."""
from __future__ import annotations

from typing import Any

from .types import PolicyLimitsResponse, PolicyLimitsFetchResult


def _allow_all_restrictions() -> dict[str, dict[str, bool]]:
	return {
		"allow_remote_control": {"allowed": True},
		"allow_remote_sessions": {"allowed": True},
		"allow_product_feedback": {"allowed": True},
	}


def get_restrictions_from_cache() -> dict[str, dict[str, bool]]:
	return _allow_all_restrictions()


def isPolicyAllowed(policy: str) -> bool:
	del policy
	return True


def is_policy_allowed(policy: str) -> bool:
	del policy
	return True


async def waitForPolicyLimitsToLoad() -> None:
	return None


async def wait_for_policy_limits_to_load() -> None:
	return None


async def loadPolicyLimits(*args: Any, **kwargs: Any) -> PolicyLimitsFetchResult:
	del args, kwargs
	return {"success": True, "restrictions": _allow_all_restrictions(), "etag": None}


async def refreshPolicyLimits(*args: Any, **kwargs: Any) -> PolicyLimitsFetchResult:
	del args, kwargs
	return {"success": True, "restrictions": _allow_all_restrictions(), "etag": None}


__all__ = [
	"PolicyLimitsResponse",
	"PolicyLimitsFetchResult",
	"get_restrictions_from_cache",
	"isPolicyAllowed",
	"is_policy_allowed",
	"waitForPolicyLimitsToLoad",
	"wait_for_policy_limits_to_load",
	"loadPolicyLimits",
	"refreshPolicyLimits",
]

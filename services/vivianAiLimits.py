"""vivian AI Limits service — mirrors src/services/vivianAiLimits.ts."""
from __future__ import annotations

import asyncio
import time
from typing import Callable, Literal, Optional, Set

QuotaStatus = Literal["allowed", "allowed_warning", "rejected"]
RateLimitType = Literal["five_hour", "seven_day", "seven_day_opus", "seven_day_sonnet", "overage"]
OverageDisabledReason = Literal[
    "overage_not_provisioned",
    "org_level_disabled",
    "org_level_disabled_until",
    "out_of_credits",
    "seat_tier_level_disabled",
    "member_level_disabled",
    "seat_tier_zero_credit_limit",
    "group_zero_credit_limit",
    "member_zero_credit_limit",
    "org_service_level_disabled",
    "org_service_zero_credit_limit",
    "no_limits_configured",
    "unknown",
]

RATE_LIMIT_DISPLAY_NAMES: dict[str, str] = {
    "five_hour": "session limit",
    "seven_day": "weekly limit",
    "seven_day_opus": "Opus limit",
    "seven_day_sonnet": "Sonnet limit",
    "overage": "extra usage limit",
}

EARLY_WARNING_CONFIGS = [
    {
        "rateLimitType": "five_hour",
        "claimAbbrev": "5h",
        "windowSeconds": 5 * 60 * 60,
        "thresholds": [{"utilization": 0.9, "timePct": 0.72}],
    },
    {
        "rateLimitType": "seven_day",
        "claimAbbrev": "7d",
        "windowSeconds": 7 * 24 * 60 * 60,
        "thresholds": [
            {"utilization": 0.75, "timePct": 0.6},
            {"utilization": 0.5, "timePct": 0.35},
            {"utilization": 0.25, "timePct": 0.15},
        ],
    },
]

EARLY_WARNING_CLAIM_MAP: dict[str, str] = {
    "5h": "five_hour",
    "7d": "seven_day",
    "overage": "overage",
}

vivianAILimits = dict  # typed dict matching TS vivianAILimits

currentLimits: vivianAILimits = {
    "status": "allowed",
    "unifiedRateLimitFallbackAvailable": False,
    "isUsingOverage": False,
}

StatusChangeListener = Callable[[vivianAILimits], None]
statusListeners: Set[StatusChangeListener] = set()

_raw_utilization: dict = {}


def getRateLimitDisplayName(rate_limit_type: str) -> str:
    """Get display name for a rate limit type.

    Mirrors getRateLimitDisplayName() from vivianAiLimits.ts.
    """
    return RATE_LIMIT_DISPLAY_NAMES.get(rate_limit_type, rate_limit_type)


def getRawUtilization() -> dict:
    """Get raw per-window utilization data.

    Mirrors getRawUtilization() from vivianAiLimits.ts.
    """
    return _raw_utilization


def emitStatusChange(limits: vivianAILimits) -> None:
    """Update currentLimits and notify all listeners.

    Mirrors emitStatusChange() from vivianAiLimits.ts.
    """
    global currentLimits
    currentLimits = limits
    for listener in list(statusListeners):
        try:
            listener(limits)
        except Exception:
            pass

    try:
        from .analytics.index import logEvent
        resets_at = limits.get("resetsAt", 0) or 0
        hours_till_reset = round((resets_at - time.time()) / 3600) if resets_at else 0
        logEvent("tengu_vivianai_limits_status_changed", {
            "status": limits.get("status"),
            "unifiedRateLimitFallbackAvailable": limits.get("unifiedRateLimitFallbackAvailable"),
            "hoursTillReset": hours_till_reset,
        })
    except Exception:
        pass


def _compute_time_progress(resets_at: float, window_seconds: float) -> float:
    now = time.time()
    window_start = resets_at - window_seconds
    elapsed = now - window_start
    return max(0.0, min(1.0, elapsed / window_seconds))


def _get_header(headers: dict, key: str) -> Optional[str]:
    """Get a header value (case-insensitive dict lookup)."""
    if isinstance(headers, dict):
        return headers.get(key) or headers.get(key.lower())
    return None


def _extract_raw_utilization(headers: dict) -> dict:
    result: dict = {}
    for key, abbrev in [("five_hour", "5h"), ("seven_day", "7d")]:
        util = _get_header(headers, f"anthropic-ratelimit-unified-{abbrev}-utilization")
        reset = _get_header(headers, f"anthropic-ratelimit-unified-{abbrev}-reset")
        if util is not None and reset is not None:
            result[key] = {"utilization": float(util), "resets_at": float(reset)}
    return result


def _get_header_based_early_warning(
    headers: dict, unified_rate_limit_fallback_available: bool
) -> Optional[vivianAILimits]:
    for claim_abbrev, rate_limit_type in EARLY_WARNING_CLAIM_MAP.items():
        surpassed = _get_header(
            headers, f"anthropic-ratelimit-unified-{claim_abbrev}-surpassed-threshold"
        )
        if surpassed is not None:
            util = _get_header(headers, f"anthropic-ratelimit-unified-{claim_abbrev}-utilization")
            reset = _get_header(headers, f"anthropic-ratelimit-unified-{claim_abbrev}-reset")
            return {
                "status": "allowed_warning",
                "resetsAt": float(reset) if reset else None,
                "rateLimitType": rate_limit_type,
                "utilization": float(util) if util else None,
                "unifiedRateLimitFallbackAvailable": unified_rate_limit_fallback_available,
                "isUsingOverage": False,
                "surpassedThreshold": float(surpassed),
            }
    return None


def _get_time_relative_early_warning(
    headers: dict, config: dict, unified_rate_limit_fallback_available: bool
) -> Optional[vivianAILimits]:
    claim_abbrev = config["claimAbbrev"]
    util = _get_header(headers, f"anthropic-ratelimit-unified-{claim_abbrev}-utilization")
    reset = _get_header(headers, f"anthropic-ratelimit-unified-{claim_abbrev}-reset")
    if util is None or reset is None:
        return None
    utilization = float(util)
    resets_at = float(reset)
    time_progress = _compute_time_progress(resets_at, config["windowSeconds"])
    should_warn = any(
        utilization >= t["utilization"] and time_progress <= t["timePct"]
        for t in config["thresholds"]
    )
    if not should_warn:
        return None
    return {
        "status": "allowed_warning",
        "resetsAt": resets_at,
        "rateLimitType": config["rateLimitType"],
        "utilization": utilization,
        "unifiedRateLimitFallbackAvailable": unified_rate_limit_fallback_available,
        "isUsingOverage": False,
    }


def _get_early_warning_from_headers(
    headers: dict, unified_rate_limit_fallback_available: bool
) -> Optional[vivianAILimits]:
    header_warning = _get_header_based_early_warning(headers, unified_rate_limit_fallback_available)
    if header_warning:
        return header_warning
    for config in EARLY_WARNING_CONFIGS:
        w = _get_time_relative_early_warning(headers, config, unified_rate_limit_fallback_available)
        if w:
            return w
    return None


def _compute_new_limits_from_headers(headers: dict) -> vivianAILimits:
    status: QuotaStatus = _get_header(headers, "anthropic-ratelimit-unified-status") or "allowed"  # type: ignore
    resets_at_hdr = _get_header(headers, "anthropic-ratelimit-unified-reset")
    resets_at = float(resets_at_hdr) if resets_at_hdr else None
    fallback_available = (
        _get_header(headers, "anthropic-ratelimit-unified-fallback") == "available"
    )
    rate_limit_type = _get_header(headers, "anthropic-ratelimit-unified-representative-claim")
    overage_status = _get_header(headers, "anthropic-ratelimit-unified-overage-status")
    overage_resets_hdr = _get_header(headers, "anthropic-ratelimit-unified-overage-reset")
    overage_resets_at = float(overage_resets_hdr) if overage_resets_hdr else None
    overage_disabled_reason = _get_header(
        headers, "anthropic-ratelimit-unified-overage-disabled-reason"
    )
    is_using_overage = status == "rejected" and overage_status in ("allowed", "allowed_warning")

    final_status: QuotaStatus = status  # type: ignore
    if status in ("allowed", "allowed_warning"):
        early_warning = _get_early_warning_from_headers(headers, fallback_available)
        if early_warning:
            return early_warning
        final_status = "allowed"

    result: vivianAILimits = {
        "status": final_status,
        "resetsAt": resets_at,
        "unifiedRateLimitFallbackAvailable": fallback_available,
        "isUsingOverage": is_using_overage,
    }
    if rate_limit_type:
        result["rateLimitType"] = rate_limit_type
    if overage_status:
        result["overageStatus"] = overage_status
    if overage_resets_at:
        result["overageResetsAt"] = overage_resets_at
    if overage_disabled_reason:
        result["overageDisabledReason"] = overage_disabled_reason
    return result


def _cache_extra_usage_disabled_reason(headers: dict) -> None:
    reason = _get_header(headers, "anthropic-ratelimit-unified-overage-disabled-reason")
    try:
        from ..utils.config import get_global_config, save_global_config
        cached = get_global_config().get("cachedExtraUsageDisabledReason")
        if cached != reason:
            save_global_config(lambda c: {**c, "cachedExtraUsageDisabledReason": reason})
    except Exception:
        pass


def extractQuotaStatusFromHeaders(headers: dict) -> None:
    """Update limits based on API response headers.

    Mirrors extractQuotaStatusFromHeaders() from vivianAiLimits.ts.
    """
    global _raw_utilization
    try:
        from ..utils.auth import isvivianAISubscriber
        is_subscriber = isvivianAISubscriber()
    except Exception:
        is_subscriber = False

    try:
        from .rateLimitMocking import shouldProcessRateLimits
        if not shouldProcessRateLimits(is_subscriber):
            _raw_utilization = {}
            if currentLimits.get("status") != "allowed" or currentLimits.get("resetsAt"):
                emitStatusChange({
                    "status": "allowed",
                    "unifiedRateLimitFallbackAvailable": False,
                    "isUsingOverage": False,
                })
            return
        from .rateLimitMocking import processRateLimitHeaders
        headers_to_use = processRateLimitHeaders(headers)
    except Exception:
        headers_to_use = headers

    _raw_utilization = _extract_raw_utilization(headers_to_use)
    new_limits = _compute_new_limits_from_headers(headers_to_use)
    _cache_extra_usage_disabled_reason(headers_to_use)

    if new_limits != currentLimits:
        emitStatusChange(new_limits)


def extractQuotaStatusFromError(error: Exception) -> None:
    """Update limits based on a 429 API error.

    Mirrors extractQuotaStatusFromError() from vivianAiLimits.ts.
    """
    global _raw_utilization
    try:
        from ..utils.auth import isvivianAISubscriber
        from .rateLimitMocking import shouldProcessRateLimits
        if not shouldProcessRateLimits(isvivianAISubscriber()):
            return
        status_code = getattr(error, "status_code", None) or getattr(error, "status", None)
        if status_code != 429:
            return
    except Exception:
        return

    try:
        new_limits = dict(currentLimits)
        err_headers = getattr(error, "headers", None) or getattr(error, "response_headers", {})
        if err_headers:
            from .rateLimitMocking import processRateLimitHeaders
            headers_to_use = processRateLimitHeaders(dict(err_headers))
            _raw_utilization = _extract_raw_utilization(headers_to_use)
            new_limits = _compute_new_limits_from_headers(headers_to_use)
            _cache_extra_usage_disabled_reason(headers_to_use)
        new_limits["status"] = "rejected"
        if new_limits != currentLimits:
            emitStatusChange(new_limits)
    except Exception:
        pass


async def checkQuotaStatus() -> None:
    """Pre-check quota status by making a minimal API request.

    Mirrors checkQuotaStatus() from vivianAiLimits.ts.
    """
    try:
        from ..utils.privacyLevel import is_essential_traffic_only
        if is_essential_traffic_only():
            return
    except Exception:
        pass

    try:
        from ..utils.auth import isvivianAISubscriber
        from .rateLimitMocking import shouldProcessRateLimits
        if not shouldProcessRateLimits(isvivianAISubscriber()):
            return
    except Exception:
        return

    try:
        from ..bootstrap.state import get_is_non_interactive_session
        if get_is_non_interactive_session():
            return
    except Exception:
        pass

    try:
        from .api.client import getAnthropicClient
        from ..utils.model.model import getSmallFastModel
        model = getSmallFastModel()
        client = await getAnthropicClient(max_retries=0)
        response = await client.messages.create(
            model=model,
            max_tokens=1,
            messages=[{"role": "user", "content": "quota"}],
        )
        extractQuotaStatusFromHeaders(getattr(response, "headers", {}))
    except Exception as e:
        extractQuotaStatusFromError(e)


# Re-exports from rateLimitMessages
from .rateLimitMessages import (
    getRateLimitErrorMessage,
    getRateLimitWarning,
    getUsingOverageText,
)

# snake_case aliases
get_rate_limit_display_name = getRateLimitDisplayName
get_raw_utilization = getRawUtilization
emit_status_change = emitStatusChange
extract_quota_status_from_headers = extractQuotaStatusFromHeaders
extract_quota_status_from_error = extractQuotaStatusFromError
check_quota_status = checkQuotaStatus

"""Rate limit messages — mirrors src/services/rateLimitMessages.ts."""
from __future__ import annotations

from typing import Literal, Optional

FEEDBACK_CHANNEL_ANT = "#briarpatch-cc"

RATE_LIMIT_ERROR_PREFIXES = (
    "You've hit your",
    "You've used",
    "You're now using extra usage",
    "You're close to",
    "You're out of extra usage",
)


def isRateLimitErrorMessage(text: str) -> bool:
    """Check if a message is a rate limit error.

    Mirrors isRateLimitErrorMessage() from rateLimitMessages.ts.
    """
    return any(text.startswith(prefix) for prefix in RATE_LIMIT_ERROR_PREFIXES)


class RateLimitMessage:
    def __init__(self, message: str, severity: Literal["error", "warning"]) -> None:
        self.message = message
        self.severity = severity


def _format_limit_reached_text(limit: str, reset_message: str, _model: str) -> str:
    import os
    if os.environ.get("USER_TYPE") == "ant":
        return (
            f"You've hit your {limit}{reset_message}. If you have feedback about this limit, "
            f"post in {FEEDBACK_CHANNEL_ANT}. You can reset your limits with /reset-limits"
        )
    return f"You've hit your {limit}{reset_message}"


def _get_limit_reached_text(limits: dict, model: str) -> str:
    import os
    resets_at = limits.get("resetsAt")
    reset_time: Optional[str] = None
    overage_reset_time: Optional[str] = None
    try:
        from ..utils.format import formatResetTime
        if resets_at:
            reset_time = formatResetTime(resets_at, True)
        if limits.get("overageResetsAt"):
            overage_reset_time = formatResetTime(limits["overageResetsAt"], True)
    except Exception:
        pass

    reset_message = f" · resets {reset_time}" if reset_time else ""
    rate_limit_type = limits.get("rateLimitType")
    overage_status = limits.get("overageStatus")

    if overage_status == "rejected":
        if resets_at and limits.get("overageResetsAt"):
            from datetime import datetime
            try:
                rt_ts = datetime.fromisoformat(resets_at).timestamp()
                ort_ts = datetime.fromisoformat(limits["overageResetsAt"]).timestamp()
                overage_reset_msg = f" · resets {reset_time}" if rt_ts < ort_ts else f" · resets {overage_reset_time}"
            except Exception:
                overage_reset_msg = f" · resets {reset_time}" if reset_time else ""
        elif reset_time:
            overage_reset_msg = f" · resets {reset_time}"
        elif overage_reset_time:
            overage_reset_msg = f" · resets {overage_reset_time}"
        else:
            overage_reset_msg = ""

        if limits.get("overageDisabledReason") == "out_of_credits":
            return f"You're out of extra usage{overage_reset_msg}"
        return _format_limit_reached_text("limit", overage_reset_msg, model)

    if rate_limit_type == "seven_day_sonnet":
        try:
            from ..utils.auth import getSubscriptionType
            sub = getSubscriptionType()
        except Exception:
            sub = None
        limit = "weekly limit" if sub in ("pro", "enterprise") else "Sonnet limit"
        return _format_limit_reached_text(limit, reset_message, model)

    if rate_limit_type == "seven_day_opus":
        return _format_limit_reached_text("Opus limit", reset_message, model)
    if rate_limit_type == "seven_day":
        return _format_limit_reached_text("weekly limit", reset_message, model)
    if rate_limit_type == "five_hour":
        return _format_limit_reached_text("session limit", reset_message, model)
    return _format_limit_reached_text("usage limit", reset_message, model)


def _get_warning_upsell_text(rate_limit_type: Optional[str]) -> Optional[str]:
    try:
        from ..utils.auth import getSubscriptionType, getOauthAccountInfo, isOverageProvisioningAllowed
        subscription_type = getSubscriptionType()
        has_extra_usage = getOauthAccountInfo().get("hasExtraUsageEnabled") is True
    except Exception:
        return None

    if rate_limit_type == "five_hour":
        if subscription_type in ("team", "enterprise"):
            try:
                if not has_extra_usage and isOverageProvisioningAllowed():
                    return "/extra-usage to request more"
            except Exception:
                pass
            return None
        if subscription_type in ("pro", "max"):
            return "/upgrade to keep using vivian Code"

    if rate_limit_type == "overage":
        if subscription_type in ("team", "enterprise"):
            try:
                from ..utils.auth import isOverageProvisioningAllowed
                if not has_extra_usage and isOverageProvisioningAllowed():
                    return "/extra-usage to request more"
            except Exception:
                pass
    return None


def _get_early_warning_text(limits: dict) -> Optional[str]:
    rate_limit_type = limits.get("rateLimitType")
    limit_name_map = {
        "seven_day": "weekly limit",
        "five_hour": "session limit",
        "seven_day_opus": "Opus limit",
        "seven_day_sonnet": "Sonnet limit",
        "overage": "extra usage",
    }
    if rate_limit_type not in limit_name_map:
        return None
    limit_name = limit_name_map[rate_limit_type]

    utilization = limits.get("utilization")
    resets_at = limits.get("resetsAt")
    try:
        from ..utils.format import formatResetTime
        reset_time = formatResetTime(resets_at, True) if resets_at else None
    except Exception:
        reset_time = None

    used = int(utilization * 100) if utilization else None
    upsell = _get_warning_upsell_text(rate_limit_type)

    if rate_limit_type == "overage":
        limit_name += " limit"

    if used and reset_time:
        base = f"You've used {used}% of your {limit_name_map[rate_limit_type]} · resets {reset_time}"
        return f"{base} · {upsell}" if upsell else base
    if used:
        base = f"You've used {used}% of your {limit_name_map[rate_limit_type]}"
        return f"{base} · {upsell}" if upsell else base
    if reset_time:
        base = f"Approaching {limit_name} · resets {reset_time}"
        return f"{base} · {upsell}" if upsell else base
    base = f"Approaching {limit_name}"
    return f"{base} · {upsell}" if upsell else base


def getRateLimitMessage(limits: dict, model: str) -> Optional[RateLimitMessage]:
    """Get the appropriate rate limit message based on limit state.

    Mirrors getRateLimitMessage() from rateLimitMessages.ts.
    """
    if limits.get("isUsingOverage"):
        if limits.get("overageStatus") == "allowed_warning":
            return RateLimitMessage("You're close to your extra usage spending limit", "warning")
        return None

    if limits.get("status") == "rejected":
        return RateLimitMessage(_get_limit_reached_text(limits, model), "error")

    if limits.get("status") == "allowed_warning":
        WARNING_THRESHOLD = 0.7
        utilization = limits.get("utilization")
        if utilization is not None and utilization < WARNING_THRESHOLD:
            return None

        try:
            from ..utils.auth import getSubscriptionType, getOauthAccountInfo
            from ..utils.billing import hasvivianAiBillingAccess
            subscription_type = getSubscriptionType()
            is_team_or_enterprise = subscription_type in ("team", "enterprise")
            has_extra_usage = getOauthAccountInfo().get("hasExtraUsageEnabled") is True
            if is_team_or_enterprise and has_extra_usage and not hasvivianAiBillingAccess():
                return None
        except Exception:
            pass

        text = _get_early_warning_text(limits)
        if text:
            return RateLimitMessage(text, "warning")

    return None


def getRateLimitErrorMessage(limits: dict, model: str) -> Optional[str]:
    """Get error message for API errors.

    Mirrors getRateLimitErrorMessage() from rateLimitMessages.ts.
    """
    message = getRateLimitMessage(limits, model)
    if message and message.severity == "error":
        return message.message
    return None


def getRateLimitWarning(limits: dict, model: str) -> Optional[str]:
    """Get warning message for UI footer.

    Mirrors getRateLimitWarning() from rateLimitMessages.ts.
    """
    message = getRateLimitMessage(limits, model)
    if message and message.severity == "warning":
        return message.message
    return None


def getUsingOverageText(limits: dict) -> str:
    """Get notification text for overage mode transitions.

    Mirrors getUsingOverageText() from rateLimitMessages.ts.
    """
    resets_at = limits.get("resetsAt")
    try:
        from ..utils.format import formatResetTime
        reset_time = formatResetTime(resets_at, True) if resets_at else ""
    except Exception:
        reset_time = ""

    rate_limit_type = limits.get("rateLimitType")
    limit_name = ""
    if rate_limit_type == "five_hour":
        limit_name = "session limit"
    elif rate_limit_type == "seven_day":
        limit_name = "weekly limit"
    elif rate_limit_type == "seven_day_opus":
        limit_name = "Opus limit"
    elif rate_limit_type == "seven_day_sonnet":
        try:
            from ..utils.auth import getSubscriptionType
            sub = getSubscriptionType()
            limit_name = "weekly limit" if sub in ("pro", "enterprise") else "Sonnet limit"
        except Exception:
            limit_name = "Sonnet limit"

    if not limit_name:
        return "Now using extra usage"

    reset_message = f" · Your {limit_name} resets {reset_time}" if reset_time else ""
    return f"You're now using extra usage{reset_message}"


is_rate_limit_error_message = isRateLimitErrorMessage
get_rate_limit_message = getRateLimitMessage
get_rate_limit_error_message = getRateLimitErrorMessage
get_rate_limit_warning = getRateLimitWarning
get_using_overage_text = getUsingOverageText

"""Mock rate limits — ANT-ONLY testing tool.

Mirrors src/services/mockRateLimits.ts.
"""
from __future__ import annotations

import time
from typing import Optional

_mock_headers: dict = {}
_mock_enabled: bool = False
_mock_headerless_429_message: Optional[str] = None
_mock_subscription_type: Optional[str] = None
_mock_fast_mode_rate_limit_duration_ms: Optional[int] = None
_mock_fast_mode_rate_limit_expires_at: Optional[float] = None
_exceeded_limits: list[dict] = []

DEFAULT_MOCK_SUBSCRIPTION = "max"


def setMockHeader(key: str, value: Optional[str]) -> None:
    """Set a mock rate limit header.

    Mirrors setMockHeader() from mockRateLimits.ts.
    """
    global _mock_enabled, _mock_headers
    full_key = f"anthropic-ratelimit-unified-{key}" if not key.startswith("anthropic") else key
    if value is None:
        _mock_headers.pop(full_key, None)
    else:
        _mock_headers[full_key] = value
    _mock_enabled = bool(_mock_headers) or _mock_headerless_429_message is not None


def getMockHeaders() -> Optional[dict]:
    """Get current mock headers.

    Mirrors getMockHeaders() from mockRateLimits.ts.
    """
    return _mock_headers if _mock_enabled and _mock_headers else None


def getMockHeaderless429Message() -> Optional[str]:
    """Get mock headerless 429 message.

    Mirrors getMockHeaderless429Message() from mockRateLimits.ts.
    """
    return _mock_headerless_429_message


def applyMockHeaders(headers: dict) -> dict:
    """Apply mock headers on top of real headers.

    Mirrors applyMockHeaders() from mockRateLimits.ts.
    """
    if not _mock_enabled or not _mock_headers:
        return headers
    return {**headers, **_mock_headers}


def shouldProcessMockLimits() -> bool:
    """Check if mock limits processing is active.

    Mirrors shouldProcessMockLimits() from mockRateLimits.ts.
    """
    return _mock_enabled


def isMockFastModeRateLimitScenario() -> bool:
    """Check if a fast-mode rate limit scenario is active.

    Mirrors isMockFastModeRateLimitScenario() from mockRateLimits.ts.
    """
    return _mock_fast_mode_rate_limit_duration_ms is not None


def checkMockFastModeRateLimit(is_fast_mode_active: bool = False) -> Optional[dict]:
    """Check if the mock fast-mode rate limit should be triggered.

    Returns mock headers if a 429 should be thrown, None otherwise.
    Mirrors checkMockFastModeRateLimit() from mockRateLimits.ts.
    """
    if _mock_fast_mode_rate_limit_expires_at is None:
        return None
    if not is_fast_mode_active:
        return None
    if time.time() > _mock_fast_mode_rate_limit_expires_at:
        return None
    return {
        "anthropic-ratelimit-unified-status": "rejected",
        "anthropic-ratelimit-unified-reset": str(int(_mock_fast_mode_rate_limit_expires_at)),
    }


def clearMockRateLimits() -> None:
    """Clear all mock rate limit settings.

    Mirrors clearMockRateLimits() / 'clear' scenario from mockRateLimits.ts.
    """
    global _mock_headers, _mock_enabled, _mock_headerless_429_message
    global _mock_subscription_type, _mock_fast_mode_rate_limit_duration_ms
    global _mock_fast_mode_rate_limit_expires_at, _exceeded_limits
    _mock_headers = {}
    _mock_enabled = False
    _mock_headerless_429_message = None
    _mock_subscription_type = None
    _mock_fast_mode_rate_limit_duration_ms = None
    _mock_fast_mode_rate_limit_expires_at = None
    _exceeded_limits = []


# snake_case aliases
set_mock_header = setMockHeader
get_mock_headers = getMockHeaders
get_mock_headerless_429_message = getMockHeaderless429Message
apply_mock_headers = applyMockHeaders
should_process_mock_limits = shouldProcessMockLimits
is_mock_fast_mode_rate_limit_scenario = isMockFastModeRateLimitScenario
check_mock_fast_mode_rate_limit = checkMockFastModeRateLimit
clear_mock_rate_limits = clearMockRateLimits

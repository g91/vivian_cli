"""Rate limit mocking facade — mirrors src/services/rateLimitMocking.ts."""
from __future__ import annotations

from typing import Optional


def processRateLimitHeaders(headers: dict) -> dict:
    """Process headers, applying mocks if /mock-limits command is active.

    Mirrors processRateLimitHeaders() from rateLimitMocking.ts.
    """
    if shouldProcessMockLimits():
        try:
            from .mockRateLimits import applyMockHeaders
            return applyMockHeaders(headers)
        except Exception:
            pass
    return headers


def shouldProcessRateLimits(is_subscriber: bool) -> bool:
    """Check if we should process rate limits.

    Mirrors shouldProcessRateLimits() from rateLimitMocking.ts.
    """
    return is_subscriber or shouldProcessMockLimits()


def checkMockRateLimitError(
    current_model: str,
    is_fast_mode_active: bool = False,
) -> Optional[Exception]:
    """Check if mock rate limits should throw a 429 error.

    Returns the error to throw, or None if no error should be thrown.
    Mirrors checkMockRateLimitError() from rateLimitMocking.ts.
    """
    if not shouldProcessMockLimits():
        return None
    try:
        from .mockRateLimits import (
            getMockHeaderless429Message,
            getMockHeaders,
            isMockFastModeRateLimitScenario,
            checkMockFastModeRateLimit,
        )

        headerless_msg = getMockHeaderless429Message()
        if headerless_msg:
            return Exception(f"Rate limit error (429): {headerless_msg}")

        mock_headers = getMockHeaders()
        if not mock_headers:
            return None

        status = mock_headers.get("anthropic-ratelimit-unified-status")
        overage_status = mock_headers.get("anthropic-ratelimit-unified-overage-status")
        rate_limit_type = mock_headers.get("anthropic-ratelimit-unified-representative-claim")

        is_opus_limit = rate_limit_type == "seven_day_opus"
        is_using_opus = "opus" in current_model

        if is_opus_limit and not is_using_opus:
            return None

        if isMockFastModeRateLimitScenario():
            fast_mode_headers = checkMockFastModeRateLimit(is_fast_mode_active)
            if fast_mode_headers is None:
                return None
            return Exception("Rate limit exceeded (mock fast mode)")

        should_throw = status == "rejected" and (not overage_status or overage_status == "rejected")
        if should_throw:
            return Exception("Rate limit exceeded (mock)")

    except Exception:
        pass
    return None


def isMockRateLimitError(error: Exception) -> bool:
    """Check if this is a mock 429 error that shouldn't be retried.

    Mirrors isMockRateLimitError() from rateLimitMocking.ts.
    """
    return shouldProcessMockLimits() and "429" in str(error)


def shouldProcessMockLimits() -> bool:
    """Check if /mock-limits command is currently active."""
    try:
        from .mockRateLimits import shouldProcessMockLimits as _impl
        return _impl()
    except Exception:
        return False


process_rate_limit_headers = processRateLimitHeaders
should_process_rate_limits = shouldProcessRateLimits
check_mock_rate_limit_error = checkMockRateLimitError
is_mock_rate_limit_error = isMockRateLimitError
should_process_mock_limits = shouldProcessMockLimits

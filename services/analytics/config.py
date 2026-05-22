"""Analytics config — mirrors src/services/analytics/config.ts."""
from __future__ import annotations

import os


def isAnalyticsDisabled() -> bool:
    """Check if analytics operations should be disabled.

    Analytics is disabled in the following cases:
    - Test environment (NODE_ENV === 'test')
    - Third-party cloud providers (Bedrock/Vertex)
    - Privacy level is no-telemetry or essential-traffic
    """
    if os.environ.get("NODE_ENV") == "test":
        return True
    if os.environ.get("vivian_CODE_USE_BEDROCK", "").lower() in ("1", "true", "yes"):
        return True
    if os.environ.get("vivian_CODE_USE_VERTEX", "").lower() in ("1", "true", "yes"):
        return True
    if os.environ.get("vivian_CODE_USE_FOUNDRY", "").lower() in ("1", "true", "yes"):
        return True
    try:
        from ...utils.privacyLevel import is_telemetry_disabled
        return is_telemetry_disabled()
    except Exception:
        return False


def isFeedbackSurveyDisabled() -> bool:
    """Check if the feedback survey should be suppressed.

    Unlike isAnalyticsDisabled(), this does NOT block on 3P providers.
    """
    if os.environ.get("NODE_ENV") == "test":
        return True
    try:
        from ...utils.privacyLevel import is_telemetry_disabled
        return is_telemetry_disabled()
    except Exception:
        return False

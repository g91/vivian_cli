"""Event metadata enrichment — mirrors src/services/analytics/metadata.ts."""
from __future__ import annotations

import os
import sys
from typing import Any, Optional


def getEventMetadata() -> dict:
    """Get enriched event metadata for analytics.

    Mirrors getEventMetadata() from metadata.ts.
    """
    metadata: dict = {}

    try:
        metadata["platform"] = sys.platform
    except Exception:
        pass

    try:
        import platform
        metadata["arch"] = platform.machine()
    except Exception:
        pass

    try:
        metadata["userType"] = os.environ.get("USER_TYPE", "external")
    except Exception:
        pass

    try:
        from ...bootstrap.state import get_session_id
        metadata["sessionId"] = get_session_id()
    except Exception:
        pass

    try:
        from ...utils.model.model import get_main_loop_model
        metadata["model"] = get_main_loop_model()
    except Exception:
        pass

    try:
        from ...utils.auth import get_subscription_type
        metadata["subscriptionType"] = get_subscription_type()
    except Exception:
        pass

    return metadata


get_event_metadata = getEventMetadata

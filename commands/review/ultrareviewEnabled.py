"""ultrareviewEnabled — mirrors src/commands/review/ultrareviewEnabled.ts.

Check if ultrareview feature is enabled for the current user.
"""

from __future__ import annotations


def is_ultrareview_enabled() -> bool:
    """Check if ultrareview is enabled."""
    return True  # Enabled for all Vivian users

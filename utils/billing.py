"""Billing access helpers — mirrors src/utils/billing.ts"""
from __future__ import annotations

import os

_mock_billing_access_override: bool | None = None


def set_mock_billing_access_override(value: bool | None) -> None:
    """Override billing access for testing."""
    global _mock_billing_access_override
    _mock_billing_access_override = value


def has_console_billing_access() -> bool:
    """Return True if the user has access to billing in the console."""
    if os.environ.get("DISABLE_COST_WARNINGS") in ("1", "true", "yes"):
        return False
    return False  # Simplified; full logic requires auth module


def has_vivian_ai_billing_access() -> bool:
    """Return True if the user has Vivian billing access."""
    if _mock_billing_access_override is not None:
        return _mock_billing_access_override
    return False  # Simplified; full logic requires auth module

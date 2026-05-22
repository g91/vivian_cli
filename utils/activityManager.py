"""Activity manager — mirrors src/utils/activityManager.ts"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

USER_ACTIVITY_TIMEOUT_MS = 5000


class ActivityManager:
    """Tracks user and CLI active time, deduplicating overlapping operations."""

    _instance: Optional["ActivityManager"] = None

    def __init__(self, get_now: Optional[Callable[[], float]] = None):
        self._get_now = get_now or (lambda: time.time() * 1000)
        self._active_operations: set[str] = set()
        self._last_user_activity_time: float = 0
        self._last_cli_recorded_time: float = self._get_now()
        self._is_cli_active: bool = False

    @classmethod
    def get_instance(cls) -> "ActivityManager":
        if cls._instance is None:
            cls._instance = ActivityManager()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    @classmethod
    def create_instance(cls, **kwargs) -> "ActivityManager":
        cls._instance = ActivityManager(**kwargs)
        return cls._instance

    def record_user_activity(self) -> None:
        """Record a user interaction."""
        if not self._is_cli_active and self._last_user_activity_time != 0:
            now = self._get_now()
            elapsed = (now - self._last_user_activity_time) / 1000
            if 0 < elapsed < USER_ACTIVITY_TIMEOUT_MS / 1000:
                pass  # Could increment a counter here
        self._last_user_activity_time = self._get_now()

    def start_cli_activity(self, operation_id: str) -> None:
        """Begin tracking a CLI operation."""
        if operation_id in self._active_operations:
            self.end_cli_activity(operation_id)
        was_empty = len(self._active_operations) == 0
        self._active_operations.add(operation_id)
        if was_empty:
            self._is_cli_active = True
            self._last_cli_recorded_time = self._get_now()

    def end_cli_activity(self, operation_id: str) -> None:
        """Stop tracking a CLI operation."""
        self._active_operations.discard(operation_id)
        if not self._active_operations:
            self._last_cli_recorded_time = self._get_now()
            self._is_cli_active = False

    async def track_operation(self, operation_id: str, fn) -> Any:
        """Track an async operation."""
        self.start_cli_activity(operation_id)
        try:
            return await fn()
        finally:
            self.end_cli_activity(operation_id)

    def get_activity_states(self) -> dict:
        now = self._get_now()
        elapsed = (now - self._last_user_activity_time) / 1000
        is_user_active = elapsed < USER_ACTIVITY_TIMEOUT_MS / 1000
        return {
            "is_user_active": is_user_active,
            "is_cli_active": self._is_cli_active,
            "active_operation_count": len(self._active_operations),
        }


activity_manager = ActivityManager.get_instance()

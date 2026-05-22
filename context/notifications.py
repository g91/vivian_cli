"""Notifications context — mirrors src/context/notifications.tsx."""
from __future__ import annotations

import threading
from copy import deepcopy
from typing import Callable, Optional

DEFAULT_TIMEOUT_MS = 8000
PRIORITIES = {
    "immediate": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


def getNext(queue: list[dict]) -> dict | None:
    if not queue:
        return None
    return min(queue, key=lambda notification: PRIORITIES.get(notification.get("priority", "low"), 3))


class NotificationsContext:
    """System notifications context."""

    def __init__(self) -> None:
        self._queue: list[dict] = []
        self._current: dict | None = None
        self._listeners: list[Callable] = []
        self._timer: threading.Timer | None = None
        self._lock = threading.RLock()

    def notify(self, title: str, body: str = "", level: str = "info") -> None:
        priority = "high" if level in {"error", "warning"} else "medium"
        self.addNotification(
            {
                "key": f"{title}:{body}:{level}",
                "text": title if not body else f"{title}: {body}",
                "title": title,
                "body": body,
                "level": level,
                "priority": priority,
            }
        )

    def addNotification(self, notification: dict) -> None:
        with self._lock:
            priority = notification.get("priority", "low")
            if priority == "immediate":
                self._cancel_timer()
                self._current = notification
                existing = []
                if self._current is not None:
                    existing = [item for item in self._queue if item.get("priority") != "immediate"]
                self._queue = [
                    item
                    for item in existing
                    if notification.get("invalidates") is None
                    or item.get("key") not in set(notification.get("invalidates", []))
                ]
                self._schedule_timeout(notification)
                self._emit(notification)
                return

            fold = notification.get("fold")
            if callable(fold):
                if self._current is not None and self._current.get("key") == notification.get("key"):
                    self._current = fold(self._current, notification)
                    self._schedule_timeout(self._current)
                    self._emit(self._current)
                    return
                for index, queued in enumerate(self._queue):
                    if queued.get("key") == notification.get("key"):
                        self._queue[index] = fold(queued, notification)
                        self._emit(self._queue[index])
                        return

            queued_keys = {item.get("key") for item in self._queue}
            if notification.get("key") in queued_keys:
                return
            if self._current is not None and self._current.get("key") == notification.get("key"):
                return

            invalidates = set(notification.get("invalidates", []))
            invalidates_current = self._current is not None and self._current.get("key") in invalidates
            if invalidates_current:
                self._cancel_timer()
                self._current = None

            self._queue = [
                item
                for item in self._queue
                if item.get("priority") != "immediate" and item.get("key") not in invalidates
            ]
            self._queue.append(notification)
            self._process_queue()

    def removeNotification(self, key: str) -> None:
        with self._lock:
            is_current = self._current is not None and self._current.get("key") == key
            in_queue = any(item.get("key") == key for item in self._queue)
            if not is_current and not in_queue:
                return
            if is_current:
                self._cancel_timer()
                self._current = None
            self._queue = [item for item in self._queue if item.get("key") != key]
            self._process_queue()

    def get_state(self) -> dict:
        with self._lock:
            return {
                "current": deepcopy(self._current),
                "queue": deepcopy(self._queue),
            }

    def subscribe(self, callback: Callable) -> Callable:
        self._listeners.append(callback)

        def unsubscribe() -> None:
            if callback in self._listeners:
                self._listeners.remove(callback)

        return unsubscribe

    def _process_queue(self) -> None:
        if self._current is not None:
            return
        next_notification = getNext(self._queue)
        if next_notification is None:
            return
        self._queue = [item for item in self._queue if item is not next_notification]
        self._current = next_notification
        self._schedule_timeout(next_notification)
        self._emit(next_notification)

    def _schedule_timeout(self, notification: dict) -> None:
        self._cancel_timer()
        timeout_ms = int(notification.get("timeoutMs") or DEFAULT_TIMEOUT_MS)

        def _expire() -> None:
            with self._lock:
                if self._current is None or self._current.get("key") != notification.get("key"):
                    return
                invalidates = set(notification.get("invalidates", []))
                self._current = None
                if invalidates:
                    self._queue = [item for item in self._queue if item.get("key") not in invalidates]
                self._process_queue()

        self._timer = threading.Timer(timeout_ms / 1000.0, _expire)
        self._timer.daemon = True
        self._timer.start()

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _emit(self, notification: dict) -> None:
        for callback in list(self._listeners):
            callback(notification)


_notifications_instance: Optional[NotificationsContext] = None


def useNotifications() -> NotificationsContext:
    global _notifications_instance
    if _notifications_instance is None:
        _notifications_instance = NotificationsContext()
    return _notifications_instance


use_notifications = useNotifications
get_next = getNext

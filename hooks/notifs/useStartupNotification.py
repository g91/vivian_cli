"""Startup notification hook — mirrors src/hooks/notifs/useStartupNotification.ts."""
from __future__ import annotations
from typing import Any, Callable

async def useStartupNotification(compute: Callable[[], Any]) -> None:
    """Fire notification(s) once on startup."""
    try:
        from ..bootstrap.state import getIsRemoteMode
    except Exception:
        getIsRemoteMode = lambda: False
    
    if getIsRemoteMode():
        return
    try:
        result = compute() if callable(compute) else None
        if result is None:
            return
        # In Python, we don't have a notification context, so just log
        if isinstance(result, list):
            for notif in result:
                print(f"[Notification] {notif}")
        else:
            print(f"[Notification] {result}")
    except Exception as e:
        print(f"[Error] {e}")

use_startup_notification = useStartupNotification

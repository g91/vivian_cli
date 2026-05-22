"""Notifier service — mirrors src/services/notifier.ts."""
from __future__ import annotations

import os
import random
from dataclasses import dataclass
from typing import Any, Optional

from ..utils.execFileNoThrow import exec_file_no_throw

DEFAULT_TITLE = "vivian Code"


@dataclass
class NotificationOptions:
    message: str
    notification_type: str
    title: Optional[str] = None


def _notification_payload(opts: NotificationOptions, **extra: Any) -> dict[str, Any]:
    payload = {
        "message": opts.message,
        "notificationType": opts.notification_type,
        "notification_type": opts.notification_type,
        "title": opts.title or DEFAULT_TITLE,
    }
    payload.update(extra)
    return payload


def _call_terminal_method(terminal: Optional[object], *method_names: str, **kwargs: Any) -> bool:
    if terminal is None:
        return False
    for method_name in method_names:
        method = getattr(terminal, method_name, None)
        if callable(method):
            method(**kwargs)
            return True
    return False


def _get_terminal_name() -> Optional[str]:
    try:
        from ..utils.envDynamic import getTerminalWithJetBrainsDetection

        terminal = getTerminalWithJetBrainsDetection()
        if terminal:
            return terminal
    except Exception:
        pass

    try:
        from ..utils.env import env

        terminal = getattr(env, "terminal", None)
        if terminal:
            return terminal
    except Exception:
        pass

    return os.environ.get("TERM_PROGRAM") or os.environ.get("TERM")


def _generate_kitty_id() -> int:
    return random.randint(0, 9999)


async def isAppleTerminalBellDisabled() -> bool:
    try:
        if _get_terminal_name() != "Apple_Terminal":
            return False

        osascript_result = await exec_file_no_throw("osascript", [
            "-e",
            "tell application \"Terminal\" to name of current settings of front window",
        ])
        current_profile = osascript_result.get("stdout", "").strip()
        if not current_profile:
            return False

        defaults_output = await exec_file_no_throw("defaults", [
            "export",
            "com.apple.Terminal",
            "-",
        ])
        if defaults_output.get("code") != 0:
            return False

        import plistlib

        parsed = plistlib.loads(defaults_output.get("stdout", "").encode("utf-8"))
        window_settings = parsed.get("Window Settings") if isinstance(parsed, dict) else None
        profile_settings = window_settings.get(current_profile) if isinstance(window_settings, dict) else None
        if not isinstance(profile_settings, dict):
            return False
        return profile_settings.get("Bell") is False
    except Exception:
        try:
            from ..utils.log import logError

            logError("Failed to read Apple Terminal bell settings")
        except Exception:
            pass
        return False


async def sendToChannel(
    channel: str,
    opts: NotificationOptions,
    terminal: Optional[object] = None,
) -> str:
    """Send a notification through the specified channel.

    Mirrors sendToChannel() from notifier.ts.
    """
    title = opts.title or DEFAULT_TITLE

    try:
        if channel == "auto":
            return await sendAuto(opts, terminal)
        elif channel == "iterm2":
            _call_terminal_method(terminal, "notifyITerm2", "notify_iterm2", opts=opts)
            return "iterm2"
        elif channel == "iterm2_with_bell":
            _call_terminal_method(terminal, "notifyITerm2", "notify_iterm2", opts=opts)
            _call_terminal_method(terminal, "notifyBell", "notify_bell")
            return "iterm2_with_bell"
        elif channel == "kitty":
            _call_terminal_method(
                terminal,
                "notifyKitty",
                "notify_kitty",
                notification=_notification_payload(opts, id=_generate_kitty_id()),
                opts=opts,
                id=_generate_kitty_id(),
            )
            return "kitty"
        elif channel == "ghostty":
            _call_terminal_method(
                terminal,
                "notifyGhostty",
                "notify_ghostty",
                notification=_notification_payload(opts),
                opts=opts,
            )
            return "ghostty"
        elif channel == "terminal_bell":
            _call_terminal_method(terminal, "notifyBell", "notify_bell")
            return "terminal_bell"
        elif channel == "notifications_disabled":
            return "disabled"
        else:
            return "none"
    except Exception:
        return "error"


async def sendAuto(
    opts: NotificationOptions,
    terminal: Optional[object] = None,
) -> str:
    """Auto-detect the best notification channel.

    Mirrors sendAuto() from notifier.ts.
    """
    term = _get_terminal_name()

    if term == "Apple_Terminal":
        bell_disabled = await isAppleTerminalBellDisabled()
        if bell_disabled:
            _call_terminal_method(terminal, "notifyBell", "notify_bell")
            return "terminal_bell"
        return "no_method_available"
    if term == "kitty":
        _call_terminal_method(
            terminal,
            "notifyKitty",
            "notify_kitty",
            notification=_notification_payload(opts, id=_generate_kitty_id()),
            opts=opts,
            id=_generate_kitty_id(),
        )
        return "kitty"
    if term == "ghostty":
        _call_terminal_method(
            terminal,
            "notifyGhostty",
            "notify_ghostty",
            notification=_notification_payload(opts),
            opts=opts,
        )
        return "ghostty"
    if term in ("iTerm.app", "iterm2"):
        _call_terminal_method(terminal, "notifyITerm2", "notify_iterm2", opts=opts)
        return "iterm2"
    return "no_method_available"


async def sendNotification(
    notif: NotificationOptions,
    terminal: Optional[object] = None,
) -> None:
    """Send a system notification through the preferred channel.

    Mirrors sendNotification() from notifier.ts.
    """
    try:
        from ..utils.hooks import execute_notification_hooks
        await execute_notification_hooks(notif)
    except Exception:
        pass

    try:
        from ..utils.config import get_global_config
        config = get_global_config()
        channel = config.get("preferredNotifChannel", "auto")
    except Exception:
        channel = "auto"

    try:
        from .analytics.index import logEvent
        method_used = await sendToChannel(channel, notif, terminal)
        term = _get_terminal_name()
        logEvent("tengu_notification_method_used", {
            "configured_channel": channel,
            "method_used": method_used,
            "term": term,
        })
    except Exception:
        pass


send_notification = sendNotification
send_to_channel = sendToChannel
send_auto = sendAuto
is_apple_terminal_bell_disabled = isAppleTerminalBellDisabled

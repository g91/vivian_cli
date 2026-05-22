"""mobile command — mirrors src/commands/mobile/mobile.tsx.

Mobile app integration for Vivian AI on iOS/Android.
"""

from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


IOS_APP_URL = "https://apps.apple.com/app/vivian-by-anthropic/id6473753684"
ANDROID_APP_URL = "https://play.google.com/store/apps/details?id=com.anthropic.vivian"
PLATFORM_URLS = {
    "ios": IOS_APP_URL,
    "android": ANDROID_APP_URL,
}


async def call(args: str, context: CommandContext) -> TextResult:
    """Mobile integration controls."""
    from ...types.command import TextResult
    parts = args.strip().split() if args.strip() else []
    action = parts[0].lower() if parts else ""
    platform = parts[1].lower() if len(parts) > 1 else "ios"

    if not action or action in {"status", "pair"}:
        return TextResult(_mobile_status(context))

    if action == "qr":
        return TextResult(_mobile_qr(platform))

    return TextResult("Usage: /mobile [status|pair|qr [ios|android]]")


def _mobile_status(context: CommandContext) -> str:
    app_state = _get_app_state(context)
    remote_session_url = app_state.get("remoteSessionUrl")
    bridge_session_url = app_state.get("replBridgeSessionUrl")

    lines = [
        "vivian Mobile",
        f"iOS: {IOS_APP_URL}",
        f"Android: {ANDROID_APP_URL}",
    ]

    if bridge_session_url:
        lines.append(f"Remote Control session: {bridge_session_url}")
    elif remote_session_url:
        lines.append(f"Remote session: {remote_session_url}")

    lines.append("Use /mobile qr ios or /mobile qr android to render a terminal QR code.")
    return "\n".join(lines)


def _mobile_qr(platform: str) -> str:
    normalized = platform if platform in PLATFORM_URLS else "ios"
    url = PLATFORM_URLS[normalized]
    lines = _generate_qr(url)
    if lines:
        header = f"vivian Mobile QR ({normalized})"
        return "\n".join([header, *lines, url])
    return f"vivian Mobile ({normalized}): {url}"


def _generate_qr(url: str) -> list[str]:
    try:
        import qrcode  # type: ignore

        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        out = StringIO()
        qr.print_ascii(out=out)
        out.seek(0)
        return [line for line in out.read().splitlines() if line]
    except Exception:
        return []


def _get_app_state(context: Any) -> dict[str, Any]:
    state_store = getattr(context, "state_store", None)
    if state_store is not None and hasattr(state_store, "get_state"):
        try:
            state = state_store.get_state()
            if isinstance(state, dict):
                return state
        except Exception:
            pass

    app_state = getattr(context, "app_state", None)
    if isinstance(app_state, dict):
        return app_state
    if app_state is not None:
        return getattr(app_state, "__dict__", {}) or {}
    return {}


mobileInfo = call
mobile_info = call

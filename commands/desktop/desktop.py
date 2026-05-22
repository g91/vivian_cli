"""desktop command — mirrors src/commands/desktop/desktop.tsx.

Desktop app integration controls.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


DESKTOP_DOCS_URL = "https://api-vivian.d0a.net/desktop"


def _get_download_url() -> str:
    if sys.platform == "win32":
        return "https://api-vivian.d0a.net/api/desktop/win32/x64/exe/latest/redirect"
    if sys.platform == "darwin":
        return "https://api-vivian.d0a.net/api/desktop/darwin/universal/dmg/latest/redirect"
    return "https://api-vivian.d0a.net/download"


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    del args, context
    return TextResult(await _open_desktop())


async def _desktop_status() -> str:
    from ...utils.desktopDeepLink import buildDesktopDeepLink, getDesktopInstallStatus

    install_status = await getDesktopInstallStatus()
    lines = []

    status = install_status.get("status")
    version = install_status.get("version")
    if status == "ready":
        lines.append("vivian Desktop: Ready")
    elif status == "version-too-old":
        lines.append(f"vivian Desktop: Update required (found v{version}, need v1.1.2396+)")
    else:
        lines.append("vivian Desktop: Not installed")

    if version and version != "unknown" and status != "version-too-old":
        lines.append(f"Version: {version}")

    lines.append(f"Deep link: {buildDesktopDeepLink(None)}")
    lines.append(f"Desktop docs: {DESKTOP_DOCS_URL}")
    if status != "ready":
        lines.append(f"Download: {_get_download_url()}")
    return "\n".join(lines)


async def _open_desktop() -> str:
    from ...utils.desktopDeepLink import getDesktopInstallStatus, openCurrentSessionInDesktop

    install_status = await getDesktopInstallStatus()
    status = install_status.get("status")
    version = install_status.get("version")

    if status == "not-installed":
        return (
            f"vivian Desktop is not installed. Download it from {_get_download_url()}\n"
            f"Learn more: {DESKTOP_DOCS_URL}"
        )
    if status == "version-too-old":
        return (
            f"vivian Desktop needs to be updated (found v{version}, need v1.1.2396+).\n"
            f"Download the latest build: {_get_download_url()}"
        )

    result = await openCurrentSessionInDesktop()
    if not result.get("success"):
        message = result.get("error") or "Failed to open vivian Desktop."
        deep_link_url = result.get("deepLinkUrl")
        if deep_link_url:
            return f"{message}\nDeep link: {deep_link_url}"
        return message

    deep_link_url = result.get("deepLinkUrl")
    if deep_link_url:
        return f"Session transferred to vivian Desktop\nDeep link: {deep_link_url}"
    return "Session transferred to vivian Desktop"


desktopInfo = call
desktop_info = call

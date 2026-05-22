"""remote-setup command — mirrors src/commands/remote-setup/.

Setup remote access for headless/bridge operation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

WEB_SETTINGS_URL = "https://vivian.d0a.net/settings"
ALT_AUTH_URL = "https://vivian.d0a.net/onboarding?step=alt-auth"

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    """Setup remote access."""
    from ...types.command import TextResult
    parts = args.strip().split(maxsplit=1) if args.strip() else []
    action = parts[0].lower() if parts else ""

    if not action or action == "status":
        return TextResult(await _remote_setup_status())

    if action == "bridge":
        return TextResult(await _bridge_setup_message())

    if action == "ssh":
        return TextResult(_ssh_setup_message())

    return TextResult("Usage: /remote-setup [status|bridge|ssh]")


async def _remote_setup_status() -> str:
    vivian_signed_in, gh_status = await _readiness()
    lines = [
        "Remote Setup Status:",
        f"  vivian sign-in: {'Ready' if vivian_signed_in else 'Not signed in'}",
        f"  GitHub CLI: {_format_gh_status(gh_status)}",
        f"  Bridge setup: {'Ready' if vivian_signed_in else 'Requires vivian sign-in'}",
        f"  SSH setup: Available at {WEB_SETTINGS_URL}",
        "",
    ]

    if not vivian_signed_in:
        lines.append("Run /login first, then retry /remote-setup.")
    elif gh_status == "not_installed":
        lines.append(f"Install GitHub CLI from https://cli.github.com/ or use {ALT_AUTH_URL}")
    elif gh_status == "not_authenticated":
        lines.append(f"Run gh auth login, or connect GitHub on the web: {ALT_AUTH_URL}")
    else:
        lines.append(f"Remote web setup is ready. Continue in {WEB_SETTINGS_URL}")

    return "\n".join(lines)


async def _bridge_setup_message() -> str:
    vivian_signed_in, gh_status = await _readiness()
    if not vivian_signed_in:
        return "Not signed in to vivian. Run /login first."
    if gh_status == "not_installed":
        return (
            "GitHub CLI not found. Install it via https://cli.github.com/, then run gh auth login, "
            f"or connect GitHub on the web: {ALT_AUTH_URL}"
        )
    if gh_status == "not_authenticated":
        return f"GitHub CLI not authenticated. Run gh auth login, or connect GitHub on the web: {ALT_AUTH_URL}"
    return f"Remote bridge setup is ready. Continue setup in {WEB_SETTINGS_URL}"


def _ssh_setup_message() -> str:
    return f"SSH remote setup: Add or review your SSH keys at {WEB_SETTINGS_URL}"


async def _readiness() -> tuple[bool, str]:
    from ...utils.auth import is_vivian_ai_subscriber
    from ...utils.github.ghAuthStatus import get_gh_auth_status

    vivian_signed_in = bool(is_vivian_ai_subscriber())
    gh_status = await get_gh_auth_status() if vivian_signed_in else "not_authenticated"
    return vivian_signed_in, gh_status


def _format_gh_status(status: str) -> str:
    if status == "authenticated":
        return "Authenticated"
    if status == "not_installed":
        return "Not installed"
    return "Not authenticated"


setupRemote = call
setup_remote = call

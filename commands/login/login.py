"""login command — mirrors src/commands/login/login.tsx.

Authenticate with Vivian AI using OAuth or API key.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    """Login to Vivian AI."""
    from ...types.command import TextResult
    import os
    from ...services.remoteManagedSettings import refreshRemoteManagedSettings

    method = args.strip().lower() if args else ""

    if method == "key":
        api_key = os.environ.get("VIVIAN_API_KEY", "")
        if api_key:
            try:
                if hasattr(context, "set_setting"):
                    context.set_setting("api_key", api_key)
            except Exception:
                pass
            try:
                await refreshRemoteManagedSettings(
                    input_fn=lambda prompt: "1",
                    output_fn=lambda line: None,
                )
            except Exception:
                pass
            return TextResult(value="Logged in with API key from VIVIAN_API_KEY environment variable.")
        return TextResult(value="Set VIVIAN_API_KEY environment variable and run /login key")

    if method == "oauth":
        try:
            await refreshRemoteManagedSettings(
                input_fn=lambda prompt: "1",
                output_fn=lambda line: None,
            )
        except Exception:
            pass
        return TextResult(value="OAuth login: Open https://vivian.d0a.net/login in your browser.")

    # Default: show options
    return TextResult(
        value=(
            "Login options:\n"
            "  /login key   - Use API key from VIVIAN_API_KEY env var\n"
            "  /login oauth - Open browser for OAuth login\n"
            "Set your API key at https://vivian.d0a.net/settings"
        )
    )


login_cmd = call

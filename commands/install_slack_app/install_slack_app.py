"""install-slack-app command — mirrors src/commands/install-slack-app/install-slack-app.ts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...services.analytics.index import log_event
from ...utils.browser import open_browser
from ...utils.config import save_global_config

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult

SLACK_APP_URL = "https://slack.com/marketplace/A08SF47R6P4-vivian"

async def call(args: str, context: CommandContext) -> TextResult:
    """Install the Slack App."""
    from ...types.command import TextResult

    log_event("tengu_install_slack_app_clicked", {})

    save_global_config(
        lambda current: {
            **current,
            "slackAppInstallCount": (current.get("slackAppInstallCount") or 0) + 1,
        }
    )

    success = await open_browser(SLACK_APP_URL)

    if success:
        return TextResult("Opening Slack app installation page in browser…")
    return TextResult(f"Couldn't open browser. Visit: {SLACK_APP_URL}")


installSlackApp = call
install_slack_app = call


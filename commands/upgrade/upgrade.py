"""upgrade command — mirrors src/commands/upgrade/upgrade.tsx.

Check for and apply upgrades to Vivian CLI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def checkUpgrade() -> str:
    from ...constants import PRODUCT_VERSION
    return f"Current version: {PRODUCT_VERSION}. Run /upgrade apply to update."


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    action = args.strip().lower() if args else ""
    if action == "apply":
        import subprocess, sys
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "vivian-cli"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                return TextResult("Vivian CLI upgraded successfully. Restart to use the new version.")
            return TextResult(f"Upgrade failed: {result.stderr[:200]}")
        except Exception as e:
            return TextResult(f"Upgrade error: {e}")
    if action == "check":
        return TextResult(checkUpgrade())
    return TextResult(checkUpgrade() + "\nUse /upgrade apply to install the latest version.")


check_upgrade = checkUpgrade

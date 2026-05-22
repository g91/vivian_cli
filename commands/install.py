"""install command — mirrors src/commands/install.tsx.

Install Vivian CLI native build or update to latest version.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    """Install or update Vivian CLI."""
    from ..types.command import TextResult
    import subprocess, sys

    target = args.strip() if args else ""

    if target == "check":
        from ..constants import PRODUCT_VERSION
        return TextResult(f"Current version: {PRODUCT_VERSION}. Run /install to update.")

    # Run pip install
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "vivian-cli"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            return TextResult("Vivian CLI installed/updated successfully.")
        return TextResult(f"Install failed: {result.stderr[:200]}")
    except Exception as e:
        return TextResult(f"Install error: {e}")


installVivian = call
install_vivian = call

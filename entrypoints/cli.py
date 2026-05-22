"""CLI entrypoint — mirrors src/entrypoints/cli.tsx."""
from __future__ import annotations

import os
import sys


async def main() -> None:
    """Bootstrap entrypoint — checks for special flags before loading the full CLI."""
    args = sys.argv[1:]

    # Fast-path for --version/-v
    if len(args) == 1 and args[0] in ("--version", "-v", "-V"):
        from ..constants import PRODUCT_VERSION
        print(f"{PRODUCT_VERSION} (Vivian CLI)")
        return

    # Load the full CLI
    from ..cli_main import main as cli_main
    await cli_main()

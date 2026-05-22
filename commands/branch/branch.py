"""branch command — mirrors src/commands/branch/branch.ts.

Create or switch git branches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    """Create or switch branches."""
    from ...types.command import TextResult
    import subprocess

    name = args.strip() if args else ""

    if not name:
        try:
            result = subprocess.run(["git", "branch", "--list"], capture_output=True, text=True)
            current = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
            branches = result.stdout.strip().split("\n")
            lines = ["Branches:", ""]
            for b in branches:
                b = b.strip().lstrip("* ")
                marker = " ← current" if b == current.stdout.strip() else ""
                lines.append(f"  {b}{marker}")
            lines.append("")
            lines.append("Use /branch <name> to switch or create.")
            return TextResult("\n".join(lines))
        except Exception as e:
            return TextResult(f"Error listing branches: {e}")

    try:
        # Try to switch first, create if it doesn't exist
        r = subprocess.run(["git", "checkout", name], capture_output=True, text=True)
        if r.returncode != 0:
            r2 = subprocess.run(["git", "checkout", "-b", name], capture_output=True, text=True)
            if r2.returncode != 0:
                return TextResult(f"Error: {r2.stderr.strip()}")
            return TextResult(f"Created and switched to branch: {name}")
        return TextResult(f"Switched to branch: {name}")
    except Exception as e:
        return TextResult(f"Error: {e}")


branchInfo = call
branch_info = call

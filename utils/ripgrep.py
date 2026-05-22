"""Ripgrep subprocess wrapper — mirrors src/utils/ripgrep.ts"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Optional


class RipgrepTimeoutError(Exception):
    """Raised when ripgrep exceeds its allotted time."""


def _get_rg_command() -> str:
    """Return the ripgrep command to use."""
    # If USE_BUILTIN_RIPGREP is explicitly false/0, require system rg
    use_builtin = os.environ.get("USE_BUILTIN_RIPGREP")
    if use_builtin in ("0", "false", "no"):
        return "rg"
    # Prefer system rg if available
    if shutil.which("rg"):
        return "rg"
    return "rg"


def ripgrep_command() -> dict:
    """Return ripgrep command config dict with rg_path and rg_args."""
    return {"rg_path": _get_rg_command(), "rg_args": []}


def run_ripgrep(
    args: list[str],
    *,
    timeout_ms: int = 30_000,
    max_output_bytes: int = 20_000_000,
    cwd: Optional[str] = None,
) -> tuple[str, str, int]:
    """Run ripgrep with the given args.

    Returns (stdout, stderr, returncode).
    Raises RipgrepTimeoutError on timeout.
    """
    config = ripgrep_command()
    cmd = [config["rg_path"]] + config["rg_args"] + args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_ms / 1000,
            cwd=cwd,
        )
        stdout = result.stdout
        if len(stdout.encode()) > max_output_bytes:
            stdout = stdout[: max_output_bytes // 4]  # truncate roughly
        return stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        raise RipgrepTimeoutError(f"ripgrep timed out after {timeout_ms}ms")

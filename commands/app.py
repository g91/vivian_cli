"""app command — launch a GUI app from the Vivian CLI.

Usage:
    /app              List available apps
    /app memedit      Launch the DMA memory editor
    /app ueSDKgen     Launch the UE3 SDK generator
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types.command import CommandContext, TextResult

# ── App registry ────────────────────────────────────────────────────────────

_APPS: dict[str, dict] = {
    "memedit": {
        "label":        "MemEdit",
        "description":  "DMA memory editor (Cheat Engine / T-Search style)",
        "script":       "memedit",          # installed entry-point script name
        "py_file":      "apps/MemEdit/MemEdit.py",
        "requires_windows": False,
    },
    "ueSDKgen": {
        "label":        "UESDKGen",
        "description":  "Unreal Engine 3 SDK generator",
        "script":       "ueSDKgen",
        "py_file":      "apps/UESDKGen/UESDKGen.py",
        "requires_windows": True,
    },
}

# Case-insensitive lookup map built once.
_ALIAS: dict[str, str] = {k.lower(): k for k in _APPS}

# Parent of the vivian_cli package directory — used as cwd so the local
# types/ package does not shadow the stdlib types module.
_REPO_ROOT = Path(__file__).resolve().parent.parent          # …/vivian_cli
_SAFE_CWD  = _REPO_ROOT.parent                               # …/


def _list_apps() -> str:
    lines = ["Available apps (launch with /app <name>):\n"]
    for key, info in _APPS.items():
        platform_note = "  [Windows only]" if info["requires_windows"] else ""
        lines.append(f"  /app {key:<12}  {info['description']}{platform_note}")
    return "\n".join(lines)


def _launch_cmd(info: dict) -> list[str]:
    """Return the best command list to launch this app.

    Strategy:
      1. Installed entry-point script (e.g. ueSDKgen.exe) — cleanest.
      2. Direct .py file run with current interpreter as fallback.
    """
    script = shutil.which(info["script"])
    if script:
        return [script]
    # Fallback: run the .py file directly from the repo root
    py_path = _REPO_ROOT / info["py_file"]
    return [sys.executable, str(py_path)]


async def call(args: str, context: "CommandContext") -> "TextResult":
    from ..types.command import TextResult

    name = args.strip()

    if not name:
        return TextResult(_list_apps())

    canonical = _ALIAS.get(name.lower())
    if canonical is None:
        known = ", ".join(_APPS)
        return TextResult(f"Unknown app '{name}'. Available: {known}")

    info = _APPS[canonical]

    if info["requires_windows"] and sys.platform != "win32":
        return TextResult(f"{info['label']} requires Windows.")

    cmd = _launch_cmd(info)
    try:
        subprocess.Popen(
            cmd,
            cwd=str(_SAFE_CWD),        # avoid types/ shadowing stdlib
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        return TextResult(f"Failed to launch {info['label']}: {exc}")

    return TextResult(f"Launched {info['label']}.")

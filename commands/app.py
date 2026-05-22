"""app command — launch a GUI app from the Vivian CLI.

Usage:
    /app              List available apps
    /app memedit      Launch the DMA memory editor
    /app ueSDKgen     Launch the UE3 SDK generator
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types.command import CommandContext, TextResult

# ── App registry ────────────────────────────────────────────────────────────

_APPS: dict[str, dict] = {
    "memedit": {
        "label":       "MemEdit",
        "description": "DMA memory editor (Cheat Engine / T-Search style)",
        "module":      "vivian_cli.apps.MemEdit.MemEdit",
        "requires_windows": False,
    },
    "ueSDKgen": {
        "label":       "UESDKGen",
        "description": "Unreal Engine 3 SDK generator",
        "module":      "vivian_cli.apps.UESDKGen.UESDKGen",
        "requires_windows": True,
    },
}

# Case-insensitive lookup map built once.
_ALIAS: dict[str, str] = {k.lower(): k for k in _APPS}


def _list_apps() -> str:
    lines = ["Available apps (launch with /app <name>):\n"]
    for key, info in _APPS.items():
        platform_note = "  [Windows only]" if info["requires_windows"] else ""
        lines.append(f"  /app {key:<12}  {info['description']}{platform_note}")
    return "\n".join(lines)


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

    # Launch in a detached subprocess so the CLI stays responsive.
    try:
        subprocess.Popen(
            [sys.executable, "-m", info["module"]],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        return TextResult(f"Failed to launch {info['label']}: {exc}")

    return TextResult(f"Launched {info['label']}.")

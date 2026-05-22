"""Miscellaneous subcommand handlers — mirrors src/cli/handlers/util.tsx.

Provides setup-token, doctor, install handlers.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional

from ..exit import cli_error, cli_ok


def setup_token_handler() -> None:
    """Interactive API key / token setup."""
    print("Vivian API key setup")
    print("─" * 40)
    key = input("Enter your API key (or press Enter to skip): ").strip()
    if not key:
        print("No key entered. Skipping setup.")
        return
    cfg_path = Path.home() / ".vivian" / "config.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    except Exception:
        cfg = {}
    cfg["api_key"] = key
    cfg_path.write_text(json.dumps(cfg, indent=2))
    print("✔ API key saved to ~/.vivian/config.json")


def doctor_handler() -> None:
    """Print a diagnostic report for the current Vivian installation."""
    print("Vivian Doctor Report")
    print("─" * 40)

    # Python version
    print(f"Python: {sys.version}")

    # vivian package version
    try:
        import importlib.metadata
        ver = importlib.metadata.version("vivian-cli")
    except Exception:
        ver = "unknown"
    print(f"vivian-cli version: {ver}")

    # Config file
    cfg_path = Path.home() / ".vivian" / "config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            print(f"Config: {cfg_path}  (model={cfg.get('model', '?')})")
        except Exception:
            print(f"Config: {cfg_path}  (parse error)")
    else:
        print(f"Config: NOT FOUND ({cfg_path})")

    # API key
    key = (
        os.environ.get("VIVIAN_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or (json.loads(cfg_path.read_text()).get("api_key") if cfg_path.exists() else None)
    )
    print(f"API key: {'set' if key else 'NOT SET'}")

    # API reachability
    try:
        import urllib.request
        api_url = "https://api-vivian.d0a.net/v1"
        req = urllib.request.Request(api_url, method="HEAD")  # nosec B310 – known URL
        urllib.request.urlopen(req, timeout=5)  # nosec B310
        print(f"API reachable: {api_url}  ✔")
    except Exception as exc:
        print(f"API reachable: ✗  ({exc})")

    # OS / platform
    print(f"OS: {platform.system()} {platform.release()} ({platform.machine()})")
    print("─" * 40)
    print("No issues detected." if key else "⚠ API key not configured.")


def install_handler() -> None:
    """Install the vivian global symlink to PATH."""
    target = Path(sys.executable).parent / "vivian"
    link_dir = Path.home() / ".local" / "bin"
    link = link_dir / "vivian"
    if not target.exists():
        cli_error(f"vivian executable not found at: {target}")
    link_dir.mkdir(parents=True, exist_ok=True)
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to(target)
    print(f"✔ Installed: {link} → {target}")
    print(f"Make sure {link_dir} is in your PATH.")

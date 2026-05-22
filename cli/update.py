"""Self-update helper — mirrors src/cli/update.ts."""
from __future__ import annotations

import importlib.metadata
import subprocess
import sys
from typing import Optional


def _current_version() -> str:
    try:
        return importlib.metadata.version("vivian-cli")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _get_latest_version(package: str = "vivian-cli") -> Optional[str]:
    """Query PyPI for the latest published version."""
    try:
        import urllib.request, json as _json
        url = f"https://pypi.org/pypi/{package}/json"
        with urllib.request.urlopen(url, timeout=10) as resp:  # nosec B310 – trusted URL
            data = _json.loads(resp.read())
            return data["info"]["version"]
    except Exception:
        return None


def update() -> None:
    """Check for an available update and install it if one exists."""
    current = _current_version()
    print(f"Current version: {current}")
    print("Checking for updates…")

    latest = _get_latest_version()
    if latest is None:
        print("Could not reach PyPI — update check failed.")
        return

    if latest == current:
        print(f"Already up to date ({current}).")
        return

    print(f"New version available: {latest}  (current: {current})")
    print("Installing update…")
    try:
        subprocess.check_call(  # nosec B603 B607 – user-initiated update
            [sys.executable, "-m", "pip", "install", "--upgrade", "vivian-cli"],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        print(f"Updated to {latest}. Restart vivian to apply.")
    except subprocess.CalledProcessError as exc:
        print(f"Update failed: {exc}", file=sys.stderr)

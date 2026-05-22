"""
Port of src/utils/bash/ShellSnapshot.ts
Shell environment snapshot for session restoration.
"""
from __future__ import annotations
import os
import subprocess
import tempfile
from typing import Any, Dict, Optional


async def create_and_save_snapshot(shell_path="bash"):
    """Create a shell environment snapshot and save it to a temp file.
    Returns the path to the snapshot file, or None on failure.
    """
    try:
        # Capture environment by running the shell with login init
        result = subprocess.run(
            [shell_path, "-l", "-i", "-c", "export -p; declare -f"],
            capture_output=True, text=True, timeout=5.0,
        )
        if result.returncode != 0 and not result.stdout:
            return None
        snapshot_content = result.stdout

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", prefix="shell_snapshot_",
            delete=False
        ) as f:
            f.write(snapshot_content)
            return f.name
    except Exception:
        return None


async def restore_snapshot(snapshot_path, shell_path="bash"):
    """Restore environment from a shell snapshot file."""
    if not snapshot_path or not os.path.exists(snapshot_path):
        return False
    try:
        result = subprocess.run(
            [shell_path, "-c", f"source {snapshot_path}"],
            capture_output=True, timeout=2.0,
        )
        return result.returncode == 0
    except Exception:
        return False


createAndSaveSnapshot = create_and_save_snapshot
restoreSnapshot = restore_snapshot

"""Port of src/utils/appleTerminalBackup.ts."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any


RestoreResult = Any


def markTerminalSetupInProgress(backupPath):
    from .config import save_global_config

    save_global_config(
        lambda current: {
            **current,
            "appleTerminalSetupInProgress": True,
            "appleTerminalBackupPath": backupPath,
        }
    )


def markTerminalSetupComplete():
    from .config import save_global_config

    save_global_config(lambda current: {**current, "appleTerminalSetupInProgress": False})


def getTerminalRecoveryInfo():
    from .config import get_global_config

    config = get_global_config()
    return {
        "inProgress": config.get("appleTerminalSetupInProgress", False),
        "backupPath": config.get("appleTerminalBackupPath") or None,
    }


def getTerminalPlistPath():
    return str(Path.home() / "Library" / "Preferences" / "com.apple.Terminal.plist")


async def backupTerminalPreferences():
    from .execFileNoThrow import exec_file_no_throw

    terminal_plist_path = getTerminalPlistPath()
    backup_path = f"{terminal_plist_path}.bak"

    try:
        result = await exec_file_no_throw("defaults", ["export", "com.apple.Terminal", terminal_plist_path])
        if result.get("code") != 0:
            return None
        if not Path(terminal_plist_path).exists():
            return None
        await exec_file_no_throw("defaults", ["export", "com.apple.Terminal", backup_path])
        markTerminalSetupInProgress(backup_path)
        return backup_path
    except Exception:
        return None


async def checkAndRestoreTerminalBackup():
    from .execFileNoThrow import exec_file_no_throw

    recovery = getTerminalRecoveryInfo()
    in_progress = recovery["inProgress"]
    backup_path = recovery["backupPath"]
    if not in_progress:
        return {"status": "no_backup"}

    if not backup_path:
        markTerminalSetupComplete()
        return {"status": "no_backup"}

    if not Path(backup_path).exists():
        markTerminalSetupComplete()
        return {"status": "no_backup"}

    try:
        result = await exec_file_no_throw("defaults", ["import", "com.apple.Terminal", backup_path])
        if result.get("code") != 0:
            markTerminalSetupComplete()
            return {"status": "failed", "backupPath": backup_path}
        await exec_file_no_throw("killall", ["cfprefsd"])
        markTerminalSetupComplete()
        return {"status": "restored"}
    except Exception:
        markTerminalSetupComplete()
        return {"status": "failed", "backupPath": backup_path}


mark_terminal_setup_in_progress = markTerminalSetupInProgress
mark_terminal_setup_complete = markTerminalSetupComplete
get_terminal_recovery_info = getTerminalRecoveryInfo
get_terminal_plist_path = getTerminalPlistPath
backup_terminal_preferences = backupTerminalPreferences
check_and_restore_terminal_backup = checkAndRestoreTerminalBackup


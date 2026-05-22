"""Port of src/utils/iTermBackup.ts."""
from __future__ import annotations

import asyncio
from pathlib import Path
from shutil import copyfile
from typing import Any


RestoreResult = Any


def markITerm2SetupComplete():
    from .config import save_global_config

    save_global_config(lambda current: {**current, "iterm2SetupInProgress": False})


def getIterm2RecoveryInfo():
    from .config import get_global_config

    config = get_global_config()
    return {
        "inProgress": config.get("iterm2SetupInProgress", False),
        "backupPath": config.get("iterm2BackupPath") or None,
    }


def getITerm2PlistPath():
    return str(Path.home() / "Library" / "Preferences" / "com.googlecode.iterm2.plist")


async def checkAndRestoreITerm2Backup():
    recovery = getIterm2RecoveryInfo()
    in_progress = recovery["inProgress"]
    backup_path = recovery["backupPath"]
    if not in_progress:
        return {"status": "no_backup"}

    if not backup_path:
        markITerm2SetupComplete()
        return {"status": "no_backup"}

    backup = Path(backup_path)
    if not backup.exists():
        markITerm2SetupComplete()
        return {"status": "no_backup"}

    try:
        await asyncio.to_thread(copyfile, str(backup), getITerm2PlistPath())
        markITerm2SetupComplete()
        return {"status": "restored"}
    except Exception:
        markITerm2SetupComplete()
        return {"status": "failed", "backupPath": str(backup)}


mark_iterm2_setup_complete = markITerm2SetupComplete
get_iterm2_recovery_info = getIterm2RecoveryInfo
get_iterm2_plist_path = getITerm2PlistPath
check_and_restore_iterm2_backup = checkAndRestoreITerm2Backup


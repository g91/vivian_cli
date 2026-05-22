"""Settings sync service — mirrors src/services/settingsSync/index.ts."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

_SYNC_STORE_PATH = Path.home() / ".vivian" / "settings-sync-cache.json"
_SYNC_SOURCES = ("userSettings", "projectSettings", "localSettings")
_download_task: Optional[asyncio.Task[bool]] = None


def _is_using_oauth() -> bool:
    try:
        from ...utils.auth import get_vivian_ai_oauth_tokens

        tokens = get_vivian_ai_oauth_tokens()
        return bool(tokens and getattr(tokens, "access_token", None))
    except Exception:
        return False


def _build_local_entries() -> dict[str, str]:
    try:
        from ...utils.settings.settings import getSettingsFilePathForSource
    except Exception:
        return {}

    entries: dict[str, str] = {}
    for source in _SYNC_SOURCES:
        path = getSettingsFilePathForSource(source)
        if not path:
            continue
        file_path = Path(path)
        if file_path.is_file():
            try:
                entries[source] = file_path.read_text(encoding="utf-8")
            except OSError:
                continue
    return entries


def _read_sync_store() -> dict[str, str]:
    try:
        payload = json.loads(_SYNC_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    entries = payload.get("entries")
    return entries if isinstance(entries, dict) else {}


async def _do_download_user_settings() -> bool:
    if not _is_using_oauth():
        return False
    try:
        from ...utils.settings.settings import getSettingsFilePathForSource, resetSettingsCache
    except Exception:
        return False

    entries = _read_sync_store()
    if not entries:
        return False

    applied = False
    for source, content in entries.items():
        path = getSettingsFilePathForSource(source)
        if not path or not isinstance(content, str):
            continue
        file_path = Path(path)
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if not file_path.exists() or file_path.read_text(encoding="utf-8") != content:
                file_path.write_text(content, encoding="utf-8")
                applied = True
        except OSError:
            continue

    if applied:
        try:
            resetSettingsCache()
        except Exception:
            pass
    return applied


async def uploadUserSettingsInBackground() -> None:
    """Upload user settings in background.

    Mirrors uploadUserSettingsInBackground() from index.ts.
    """
    if not _is_using_oauth():
        return
    entries = _build_local_entries()
    if not entries:
        return
    _SYNC_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"entries": entries}
    await asyncio.to_thread(
        _SYNC_STORE_PATH.write_text,
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _resetDownloadPromiseForTesting() -> None:
    """Reset download promise for testing."""
    global _download_task
    if _download_task is not None:
        _download_task.cancel()
    _download_task = None


def downloadUserSettings() -> bool:
    """Download user settings.

    Mirrors downloadUserSettings() from index.ts.
    """
    global _download_task
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return False
    if _download_task is None or _download_task.done():
        _download_task = loop.create_task(_do_download_user_settings())
    return True


def redownloadUserSettings() -> bool:
    """Redownload user settings.

    Mirrors redownloadUserSettings() from index.ts.
    """
    global _download_task
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return False
    _download_task = loop.create_task(_do_download_user_settings())
    return True


upload_user_settings_in_background = uploadUserSettingsInBackground
download_user_settings = downloadUserSettings
redownload_user_settings = redownloadUserSettings

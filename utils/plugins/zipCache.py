"""
Port of src/utils/plugins/zipCache.ts

Plugin Zip Cache Module - manages plugins as ZIP archives.
"""
from __future__ import annotations

import os
import secrets
import shutil
import tempfile
import zipfile
from typing import Any, Dict, List, Optional

from ..debug import logForDebugging
from ..envUtils import is_env_truthy
from ..permissions.pathValidation import expandTilde


def isPluginZipCacheEnabled() -> bool:
    return is_env_truthy(os.environ.get("vivian_CODE_PLUGIN_USE_ZIP_CACHE"))


def getPluginZipCachePath() -> Optional[str]:
    if not isPluginZipCacheEnabled():
        return None
    dir_path = os.environ.get("vivian_CODE_PLUGIN_CACHE_DIR")
    return expandTilde(dir_path) if dir_path else None


def getZipCacheKnownMarketplacesPath() -> str:
    cache_path = getPluginZipCachePath()
    if not cache_path:
        raise RuntimeError("Plugin zip cache is not enabled")
    return os.path.join(cache_path, "known_marketplaces.json")


def getZipCacheInstalledPluginsPath() -> str:
    cache_path = getPluginZipCachePath()
    if not cache_path:
        raise RuntimeError("Plugin zip cache is not enabled")
    return os.path.join(cache_path, "installed_plugins.json")


def getZipCacheMarketplacesDir() -> str:
    cache_path = getPluginZipCachePath()
    if not cache_path:
        raise RuntimeError("Plugin zip cache is not enabled")
    return os.path.join(cache_path, "marketplaces")


def getZipCachePluginsDir() -> str:
    cache_path = getPluginZipCachePath()
    if not cache_path:
        raise RuntimeError("Plugin zip cache is not enabled")
    return os.path.join(cache_path, "plugins")


_session_plugin_cache_path: Optional[str] = None
_session_plugin_cache_promise: Optional[str] = None


async def getSessionPluginCachePath() -> str:
    global _session_plugin_cache_path, _session_plugin_cache_promise
    if _session_plugin_cache_path:
        return _session_plugin_cache_path
    if not _session_plugin_cache_promise:
        suffix = secrets.token_hex(8)
        dir_path = os.path.join(tempfile.gettempdir(), f"vivian-plugin-session-{suffix}")
        os.makedirs(dir_path, exist_ok=True)
        _session_plugin_cache_path = dir_path
        _session_plugin_cache_promise = dir_path
        logForDebugging(f"Created session plugin cache at {dir_path}")
    return _session_plugin_cache_promise


async def cleanupSessionPluginCache() -> None:
    global _session_plugin_cache_path, _session_plugin_cache_promise
    if not _session_plugin_cache_path:
        return
    try:
        shutil.rmtree(_session_plugin_cache_path, ignore_errors=True)
        logForDebugging(f"Cleaned up session plugin cache at {_session_plugin_cache_path}")
    except Exception as e:
        logForDebugging(f"Failed to clean up session plugin cache: {e}")
    finally:
        _session_plugin_cache_path = None
        _session_plugin_cache_promise = None


def resetSessionPluginCache() -> None:
    global _session_plugin_cache_path, _session_plugin_cache_promise
    _session_plugin_cache_path = None
    _session_plugin_cache_promise = None


async def atomicWriteToZipCache(target_path: str, data: bytes | str) -> None:
    dir_path = os.path.dirname(target_path)
    os.makedirs(dir_path, exist_ok=True)
    tmp_name = f".{os.path.basename(target_path)}.tmp.{secrets.token_hex(4)}"
    tmp_path = os.path.join(dir_path, tmp_name)
    try:
        mode = "wb" if isinstance(data, bytes) else "w"
        encoding = None if isinstance(data, bytes) else "utf-8"
        with open(tmp_path, mode, encoding=encoding) as f:
            f.write(data)
        os.replace(tmp_path, target_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise


async def createZipFromDirectory(source_dir: str) -> bytes:
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            if ".git" in dirs:
                dirs.remove(".git")
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, source_dir)
                zf.write(full_path, arcname)
    result = buf.getvalue()
    logForDebugging(f"Created ZIP from {source_dir}: {len(result)} bytes")
    return result


async def extractZipToDirectory(zip_path: str, target_dir: str) -> None:
    os.makedirs(target_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(target_dir)
    logForDebugging(f"Extracted ZIP to {target_dir}")


async def convertDirectoryToZipInPlace(dir_path: str, zip_path: str) -> None:
    zip_data = await createZipFromDirectory(dir_path)
    await atomicWriteToZipCache(zip_path, zip_data)
    shutil.rmtree(dir_path, ignore_errors=True)


def getMarketplaceJsonRelativePath(marketplace_name: str) -> str:
    sanitized = "".join(c if c.isalnum() or c in "-_" else "-" for c in marketplace_name)
    return os.path.join("marketplaces", f"{sanitized}.json")


def isMarketplaceSourceSupportedByZipCache(source: Dict[str, Any]) -> bool:
    return source.get("source") in ("github", "git", "url", "settings")


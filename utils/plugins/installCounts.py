"""
Port of src/utils/plugins/installCounts.ts

Plugin install counts data layer.
"""
from __future__ import annotations

import json
import os
import secrets
import time
from typing import Any, Dict, List, Optional

from ..debug import logForDebugging
from ..errors import errorMessage
from ..log import logError
from .fetchTelemetry import classifyFetchError, logPluginFetch
from .pluginDirectories import getPluginsDirectory

INSTALL_COUNTS_CACHE_VERSION = 1
INSTALL_COUNTS_CACHE_FILENAME = "install-counts-cache.json"
INSTALL_COUNTS_URL = "https://raw.githubusercontent.com/anthropics/vivian-plugins-official/refs/heads/stats/stats/plugin-installs.json"
CACHE_TTL_MS = 24 * 60 * 60 * 1000


def _get_install_counts_cache_path() -> str:
    return os.path.join(getPluginsDirectory(), INSTALL_COUNTS_CACHE_FILENAME)


async def _load_install_counts_cache() -> Optional[Dict[str, Any]]:
    path = _get_install_counts_cache_path()
    try:
        if not os.path.isfile(path):
            return None
        with open(path, "r") as f:
            data = json.loads(f.read())
        if not isinstance(data, dict) or data.get("version") != INSTALL_COUNTS_CACHE_VERSION:
            return None
        return data
    except Exception:
        return None


async def _save_install_counts_cache(cache: Dict[str, Any]) -> None:
    path = _get_install_counts_cache_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.{secrets.token_hex(8)}.tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(cache, f, indent=2)
        os.replace(tmp_path, path)
    except Exception as e:
        logError(e)
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


async def _fetch_install_counts_from_github() -> List[Dict[str, Any]]:
    import httpx
    started = time.time()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(INSTALL_COUNTS_URL)
            data = resp.json()
            if not isinstance(data, dict) or "plugins" not in data:
                raise ValueError("Invalid response format")
            logPluginFetch("install_counts", INSTALL_COUNTS_URL, "success", (time.time() - started) * 1000)
            return data["plugins"]
    except Exception as e:
        logPluginFetch("install_counts", INSTALL_COUNTS_URL, "failure", (time.time() - started) * 1000, classifyFetchError(e))
        raise


async def getInstallCounts() -> Optional[Dict[str, int]]:
    cache = await _load_install_counts_cache()
    if cache:
        logPluginFetch("install_counts", INSTALL_COUNTS_URL, "cache_hit", 0)
        return {e["plugin"]: e["unique_installs"] for e in cache.get("counts", [])}

    try:
        counts = await _fetch_install_counts_from_github()
        new_cache = {"version": INSTALL_COUNTS_CACHE_VERSION, "fetchedAt": "", "counts": counts}
        await _save_install_counts_cache(new_cache)
        return {e["plugin"]: e["unique_installs"] for e in counts}
    except Exception as e:
        logError(e)
        return None


def formatInstallCount(count: int) -> str:
    if count < 1000:
        return str(count)
    if count < 1000000:
        k = count / 1000
        formatted = f"{k:.1f}"
        return f"{formatted.rstrip('0').rstrip('.')}K"
    m = count / 1000000
    formatted = f"{m:.1f}"
    return f"{formatted.rstrip('0').rstrip('.')}M"


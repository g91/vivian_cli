"""Port of src/utils/plugins/zipCacheAdapters.ts."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from ..debug import logForDebugging
from .marketplaceManager import loadKnownMarketplacesConfigSafe
from .zipCache import (
    atomicWriteToZipCache,
    getMarketplaceJsonRelativePath,
    getPluginZipCachePath,
    getZipCacheKnownMarketplacesPath,
)


async def readZipCacheKnownMarketplaces() -> Dict[str, Any]:
    """Read known_marketplaces.json from the zip cache.
Returns empty object if file doesn't exist, can't be parsed, or fails schema
validation (data comes from a shared mounted volume — other containers may write)."""
    try:
        with open(getZipCacheKnownMarketplacesPath(), "r", encoding="utf-8") as f:
            parsed = json.loads(f.read())
        if not isinstance(parsed, dict):
            raise ValueError("known_marketplaces.json must contain an object")
        return parsed
    except Exception as error:
        if not isinstance(error, FileNotFoundError):
            logForDebugging(
                f"Invalid known_marketplaces.json in zip cache: {error}",
                level="error",
            )
        return {}


async def writeZipCacheKnownMarketplaces(data: Dict[str, Any]) -> None:
    """Write known_marketplaces.json to the zip cache atomically."""
    await atomicWriteToZipCache(
        getZipCacheKnownMarketplacesPath(),
        json.dumps(data, indent=2),
    )


async def readMarketplaceJson(marketplaceName: str) -> Optional[Dict[str, Any]]:
    """Read a marketplace JSON file from the zip cache."""
    zip_cache_path = getPluginZipCachePath()
    if not zip_cache_path:
        return None
    full_path = os.path.join(zip_cache_path, getMarketplaceJsonRelativePath(marketplaceName))
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            parsed = json.loads(f.read())
        if isinstance(parsed, dict):
            return parsed
        logForDebugging(f"Invalid marketplace JSON for {marketplaceName}: expected object")
    except Exception:
        return None
    return None


async def saveMarketplaceJsonToZipCache(marketplaceName: str, installLocation: str) -> None:
    """Save a marketplace JSON to the zip cache from its install location."""
    zip_cache_path = getPluginZipCachePath()
    if not zip_cache_path:
        return
    content = await readMarketplaceJsonContent(installLocation)
    if content is not None:
        rel_path = getMarketplaceJsonRelativePath(marketplaceName)
        await atomicWriteToZipCache(os.path.join(zip_cache_path, rel_path), content)


async def readMarketplaceJsonContent(dir: str) -> Optional[str]:
    """Read marketplace.json content from a cloned marketplace directory or file.
For directory sources: checks .vivian-plugin/marketplace.json, marketplace.json
For URL sources: the installLocation IS the marketplace JSON file itself."""
    candidates = [
        os.path.join(dir, ".vivian-plugin", "marketplace.json"),
        os.path.join(dir, "marketplace.json"),
        dir,
    ]
    for candidate in candidates:
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            continue
    return None


async def syncMarketplacesToZipCache() -> None:
    """Sync marketplace data to zip cache for offline access.
Saves marketplace JSONs and merges with previously cached data
so ephemeral containers can access marketplaces without re-cloning."""
    known_marketplaces = await loadKnownMarketplacesConfigSafe()

    for name, entry in known_marketplaces.items():
        install_location = entry.get("installLocation") if isinstance(entry, dict) else None
        if not install_location:
            continue
        try:
            await saveMarketplaceJsonToZipCache(name, install_location)
        except Exception as error:
            logForDebugging(f"Failed to save marketplace JSON for {name}: {error}")

    zip_cache_known_marketplaces = await readZipCacheKnownMarketplaces()
    merged_known_marketplaces = {
        **zip_cache_known_marketplaces,
        **known_marketplaces,
    }
    await writeZipCacheKnownMarketplaces(merged_known_marketplaces)


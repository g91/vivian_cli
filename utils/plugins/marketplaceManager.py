"""
Port of src/utils/plugins/marketplaceManager.ts

Self-contained utility functions (path resolution, URL redaction, header
redaction, cache reading) are fully implemented. The full marketplace pipeline
(git clone/pull, HTTP fetch, schema validation, settings management, seed
directory registration, marketplace reconciliation) requires the complete
plugin infrastructure and is documented as stubs.
"""
from __future__ import annotations

from typing import Any, Optional, Dict, List, Callable
import os
import os.path
import json
import re
import asyncio
import hashlib
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from .pluginIdentifier import parsePluginIdentifier


LoadedPluginMarketplace = Dict[str, Any]
KnownMarketplacesConfig = Dict[str, Any]
DeclaredMarketplace = Dict[str, Any]
MarketplaceProgressCallback = Any

# ── Path helpers ────────────────────────────────────────────────────────────

def _get_plugins_directory() -> str:
    """Get the plugins directory path."""
    return str(Path.home() / ".vivian" / "plugins")


def getKnownMarketplacesFile() -> str:
    """Get the path to the known marketplaces configuration file."""
    return os.path.join(_get_plugins_directory(), "known_marketplaces.json")


def getMarketplacesCacheDir() -> str:
    """Get the path to the marketplaces cache directory."""
    return os.path.join(_get_plugins_directory(), "marketplaces")


def clearMarketplacesCache() -> None:
    """Clear all cached marketplace data (for testing).
    
    Stub: requires memoized getMarketplace cache infrastructure.
    """
    return None


# ── URL / header redaction ──────────────────────────────────────────────────

def redactHeaders(headers: Dict[str, str]) -> Dict[str, str]:
    """Redact header values for safe logging.
    
    Replaces Authorization and sensitive header values with '[redacted]'.
    """
    sensitive = {"authorization", "x-api-key", "cookie", "set-cookie"}
    return {
        k: "[redacted]" if k.lower() in sensitive else v
        for k, v in headers.items()
    }


def redactUrlCredentials(url_string: str) -> str:
    """Redact userinfo (username:password) in a URL to avoid logging credentials."""
    try:
        parsed = urlparse(url_string)
        if parsed.username or parsed.password:
            # Replace userinfo with '[redacted]'
            netloc = parsed.hostname or ""
            if parsed.port:
                netloc += f":{parsed.port}"
            redacted = parsed._replace(netloc=netloc)
            return urlunparse(redacted)
        return url_string
    except Exception:
        return url_string


# ── Cache reading ───────────────────────────────────────────────────────────

async def readCachedMarketplace(install_location: str) -> Optional[str]:
    """Read a cached marketplace from disk without updating it."""
    if not install_location or not os.path.exists(install_location):
        return None
    try:
        with open(install_location, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


# ── Declared marketplaces ───────────────────────────────────────────────────

def getDeclaredMarketplaces() -> Dict[str, Dict[str, Any]]:
    """Get declared marketplace intent from merged settings and --add-dir sources.
    
    Stub: requires full settings infrastructure.
    """
    declared: Dict[str, Dict[str, Any]] = {}

    try:
        from .addDirPluginSettings import getAddDirExtraMarketplaces

        for name, source in getAddDirExtraMarketplaces().items():
            if isinstance(source, dict):
                declared[name] = {"source": source}
    except Exception:
        pass

    try:
        from ..settings.settings import getInitialSettings

        settings = getInitialSettings() or {}
        for name, source in (settings.get("extraKnownMarketplaces") or {}).items():
            if isinstance(source, dict):
                declared[name] = {"source": source}
    except Exception:
        pass

    return declared


def getMarketplaceDeclaringSource(name: str) -> Optional[str]:
    """Find which editable settings source declared a marketplace.
    
    Stub: requires full settings infrastructure.
    """
    return None


def saveMarketplaceToSettings(
    name: str,
    entry: Dict[str, Any],
    setting_source: str = "userSettings",
) -> None:
    """Save a marketplace entry to settings (intent layer).
    
    Stub: requires full settings infrastructure.
    """
    try:
        from ..settings.settings import getSettingsForSource, updateSettingsForSource

        settings = getSettingsForSource(setting_source) or {}
        marketplaces = dict(settings.get("extraKnownMarketplaces", {}))
        marketplaces[name] = entry.get("source", entry)
        updateSettingsForSource(setting_source, {**settings, "extraKnownMarketplaces": marketplaces})
    except Exception:
        return None


# ── Known marketplaces config ───────────────────────────────────────────────

async def loadKnownMarketplacesConfig() -> Dict[str, Any]:
    """Load known marketplaces configuration from disk."""
    path = getKnownMarketplacesFile()
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.loads(f.read())
    except Exception:
        pass
    return {}


async def loadKnownMarketplacesConfigSafe() -> Dict[str, Any]:
    """Load known marketplaces config, returning {} on any error instead of throwing."""
    try:
        return await loadKnownMarketplacesConfig()
    except Exception:
        return {}


async def saveKnownMarketplacesConfig(config: Dict[str, Any]) -> None:
    """Save known marketplaces configuration to disk."""
    path = getKnownMarketplacesFile()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass


# ── Seed marketplaces ───────────────────────────────────────────────────────

async def registerSeedMarketplaces() -> None:
    """Register marketplaces from the read-only seed directories.
    
    Stub: requires full seed directory infrastructure.
    """
    from .pluginDirectories import getPluginSeedDirs

    known = await loadKnownMarketplacesConfig()
    changed = False

    for seed_dir in getPluginSeedDirs():
        seed_known = await readSeedKnownMarketplaces(seed_dir)
        for name, entry in seed_known.items():
            if not isinstance(entry, dict):
                continue
            install_location = await findSeedMarketplaceLocation(seed_dir, name)
            candidate = {
                **entry,
                "installLocation": install_location or entry.get("installLocation"),
            }
            if known.get(name) != candidate:
                known[name] = candidate
                changed = True

    if changed:
        await saveKnownMarketplacesConfig(known)
    return changed


async def readSeedKnownMarketplaces(seed_dir: str) -> Dict[str, Any]:
    """Read known_marketplaces.json from a seed directory."""
    path = os.path.join(seed_dir, "known_marketplaces.json")
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.loads(f.read())
    except Exception:
        pass
    return {}


async def findSeedMarketplaceLocation(seed_dir: str, name: str) -> Optional[str]:
    """Locate a marketplace in the seed directory by name."""
    # Check for marketplace.json in seed dir
    candidates = [
        os.path.join(seed_dir, name, ".vivian-plugin", "marketplace.json"),
        os.path.join(seed_dir, name, "marketplace.json"),
        os.path.join(seed_dir, f"{name}.json"),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None


def seedDirFor(install_location: str) -> Optional[str]:
    """If install_location points into a configured seed directory, return that seed.
    
    Stub: requires full seed directory infrastructure.
    """
    return None


# ── Git operations ──────────────────────────────────────────────────────────

DEFAULT_PLUGIN_GIT_TIMEOUT_MS = 30000


def getPluginGitTimeoutMs() -> int:
    """Get the git timeout for plugin operations from env or default."""
    env_value = os.environ.get("vivian_CODE_PLUGIN_GIT_TIMEOUT_MS", "")
    if env_value:
        try:
            parsed = int(env_value)
            if parsed > 0:
                return parsed
        except ValueError:
            pass
    return DEFAULT_PLUGIN_GIT_TIMEOUT_MS


async def gitClone(
    git_url: str,
    target_path: str,
    ref: Optional[str] = None,
    sparse_paths: Optional[List[str]] = None,
) -> bool:
    """Git clone operation.
    
    Stub: requires full git operation infrastructure.
    """
    return False


async def gitPull(
    cwd: str,
    ref: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Git pull operation.
    
    Stub: requires full git operation infrastructure.
    """
    return {"code": -1, "stderr": "not implemented"}


async def gitSubmoduleUpdate(
    cwd: str,
    credential_args: List[str],
    env: Dict[str, str],
    sparse_paths: List[str],
) -> bool:
    """Sync submodule working dirs after a successful pull.
    
    Stub: requires full git operation infrastructure.
    """
    return False


def enhanceGitPullErrorMessages(result: Optional[Dict[str, Any]] = None) -> str:
    """Enhance error messages for git pull failures."""
    if not result:
        return "Git pull failed"
    stderr = result.get("stderr", "")
    if "Permission denied" in stderr:
        return f"Authentication failed: {stderr.strip()}"
    if "Could not resolve host" in stderr:
        return f"Network error: {stderr.strip()}"
    return stderr.strip() or f"Git pull failed with code {result.get('code', 'unknown')}"


async def isGitHubSshLikelyConfigured() -> bool:
    """Check if SSH is likely to work for GitHub.
    
    Stub: requires SSH key checking infrastructure.
    """
    return False


def isAuthenticationError(stderr: str) -> bool:
    """Check if a git error indicates authentication failure."""
    auth_patterns = [
        "Permission denied",
        "Authentication failed",
        "could not read Username",
        "could not read Password",
        "fatal: could not read",
        "repository not found",
        "access denied",
    ]
    return any(p.lower() in stderr.lower() for p in auth_patterns)


def extractSshHost(git_url: str) -> Optional[str]:
    """Extract the SSH host from a git URL for error messaging."""
    m = re.match(r"^(?:ssh://)?(?:git@)?([^:/]+)[:/]", git_url)
    return m.group(1) if m else None


# ── Marketplace caching ─────────────────────────────────────────────────────

async def cacheMarketplaceFromGit(
    git_url: str,
    cache_path: str,
    ref: Optional[str] = None,
    sparse_paths: Optional[List[str]] = None,
    on_progress: Optional[Callable] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Cache a marketplace from a git repository.
    
    Stub: requires full git + caching infrastructure.
    """
    return None


async def cacheMarketplaceFromUrl(
    url: str,
    cache_path: str,
    custom_headers: Optional[Dict[str, str]] = None,
    on_progress: Optional[Callable] = None,
) -> Optional[str]:
    """Cache a marketplace from a URL.
    
    Stub: requires full HTTP fetch + caching infrastructure.
    """
    return None


def getCachePathForSource(source: Dict[str, Any]) -> str:
    """Generate a cache path for a marketplace source."""
    source_type = source.get("source", "unknown")
    if source_type == "github":
        repo = source.get("repo", "unknown").replace("/", "-")
        return os.path.join(getMarketplacesCacheDir(), f"github-{repo}")
    elif source_type == "url":
        url = source.get("url", "unknown")
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:12]
        return os.path.join(getMarketplacesCacheDir(), f"url-{url_hash}")
    elif source_type == "git":
        url = source.get("url", "unknown")
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:12]
        return os.path.join(getMarketplacesCacheDir(), f"git-{url_hash}")
    elif source_type in ("directory", "file"):
        path = source.get("path", "unknown")
        path_hash = hashlib.sha256(path.encode()).hexdigest()[:12]
        return os.path.join(getMarketplacesCacheDir(), f"local-{path_hash}")
    return os.path.join(getMarketplacesCacheDir(), f"unknown-{hashlib.sha256(str(source).encode()).hexdigest()[:12]}")


async def parseFileWithSchema(
    file_path: str,
    schema: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """Parse and validate JSON file.
    
    Stub: requires full schema validation infrastructure.
    """
    try:
        if os.path.isfile(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.loads(f.read())
    except Exception:
        pass
    return None


async def loadAndCacheMarketplace(
    source: Dict[str, Any],
    on_progress: Optional[Callable] = None,
) -> Optional[Dict[str, Any]]:
    """Load and cache a marketplace from its source.
    
    Stub: requires full marketplace loading + caching infrastructure.
    """
    return None


# ── Marketplace CRUD ────────────────────────────────────────────────────────

async def addMarketplaceSource(
    source: Dict[str, Any],
    on_progress: Optional[Callable] = None,
) -> Optional[str]:
    """Add a marketplace source to the known marketplaces.
    
    Stub: requires full marketplace reconciliation infrastructure.
    """
    name = source.get("name")
    if not name:
        if source.get("source") == "github":
            name = str(source.get("repo", "marketplace")).split("/")[-1]
        elif source.get("source") in ("directory", "file"):
            name = os.path.basename(str(source.get("path", "marketplace")).rstrip(os.sep)) or "marketplace"
        else:
            name = "marketplace"

    known = await loadKnownMarketplacesConfig()
    install_location = source.get("path") if source.get("source") in ("directory", "file") else getCachePathForSource(source)
    known[name] = {
        "source": source,
        "installLocation": install_location,
        "lastUpdated": "",
        "autoUpdate": source.get("autoUpdate"),
    }
    await saveKnownMarketplacesConfig(known)
    safeCallProgress(on_progress, f"Added marketplace {name}")
    return name


async def removeMarketplaceSource(name: str) -> bool:
    """Remove a marketplace source from known marketplaces.
    
    Stub: requires full marketplace reconciliation infrastructure.
    """
    return False


async def getMarketplaceCacheOnly(name: str) -> Optional[Dict[str, Any]]:
    """Get a specific marketplace by name from cache only (no network)."""
    config = await loadKnownMarketplacesConfigSafe()
    marketplace_config = config.get(name)
    if not marketplace_config:
        return None
    
    source = marketplace_config.get("source", {})
    install_location = marketplace_config.get("installLocation")
    cache_path = install_location or getCachePathForSource(source)
    
    # Try to read cached marketplace data
    if os.path.isdir(cache_path):
        for candidate in [
            os.path.join(cache_path, ".vivian-plugin", "marketplace.json"),
            os.path.join(cache_path, "marketplace.json"),
        ]:
            data = await parseFileWithSchema(candidate)
            if data:
                data.setdefault("_cachePath", cache_path)
                return data
    elif cache_path.endswith(".json") and os.path.isfile(cache_path):
        data = await parseFileWithSchema(cache_path)
        if data:
            data.setdefault("_cachePath", cache_path)
        return data
    
    return None


async def getPluginByIdCacheOnly(plugin_id: str) -> Optional[Dict[str, Any]]:
    """Get plugin by ID from cache only (no network calls)."""
    parsed = parsePluginIdentifier(plugin_id)
    if not parsed:
        return None
    
    marketplace = await getMarketplaceCacheOnly(parsed["marketplace"])
    if not marketplace:
        return None
    
    plugins = marketplace.get("plugins", [])
    entry = None
    if isinstance(plugins, dict):
        entry = plugins.get(parsed["name"])
    elif isinstance(plugins, list):
        entry = next(
            (item for item in plugins if isinstance(item, dict) and item.get("name") == parsed["name"]),
            None,
        )
    if entry:
        return {
            "entry": entry,
            "marketplaceInstallLocation": marketplace.get("_cachePath"),
        }
    return None


async def getPluginById(plugin_id: str) -> Optional[Dict[str, Any]]:
    """Get plugin by ID from a specific marketplace.
    
    Stub: requires full marketplace loading infrastructure.
    Falls back to cache-only lookup.
    """
    return await getPluginByIdCacheOnly(plugin_id)


async def refreshAllMarketplaces() -> List[Dict[str, Any]]:
    """Refresh all marketplace caches.
    
    Stub: requires full marketplace refresh infrastructure.
    """
    return []


async def refreshMarketplace(
    name: str,
    on_progress: Optional[Callable] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Refresh a single marketplace cache.
    
    Stub: requires full marketplace refresh infrastructure.
    """
    safeCallProgress(on_progress, f"Refreshing marketplace {name}")
    return await getMarketplaceCacheOnly(name)


async def setMarketplaceAutoUpdate(name: str, auto_update: bool) -> None:
    """Set the autoUpdate flag for a marketplace.
    
    Stub: requires full settings infrastructure.
    """
    known = await loadKnownMarketplacesConfig()
    if name in known and isinstance(known[name], dict):
        known[name] = {**known[name], "autoUpdate": auto_update}
        await saveKnownMarketplacesConfig(known)


def safeCallProgress(
    on_progress: Optional[Callable[[str], None]],
    message: str,
) -> None:
    """Safely invoke a progress callback, catching and logging any errors."""
    if not on_progress:
        return
    try:
        on_progress(message)
    except Exception:
        pass


async def reconcileSparseCheckout(
    cwd: str,
    sparse_paths: List[str],
) -> bool:
    """Reconcile the on-disk sparse-checkout state with the desired config.
    
    Stub: requires full git sparse-checkout infrastructure.
    """
    return False


# ── Module-level exports (lazy-loaded) ──────────────────────────────────────

getMarketplace: Any = None
_test: Any = None


async def getMarketplace(name: str) -> Optional[Dict[str, Any]]:
    return await getMarketplaceCacheOnly(name)


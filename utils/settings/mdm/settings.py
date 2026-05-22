"""Port of src/utils/settings/mdm/settings.ts"""
from __future__ import annotations
import threading
from typing import Optional, Dict, Any

from .rawRead import fireRawRead

_mdm_cache: Optional[Dict[str, Any]] = None
_hkcu_cache: Optional[Dict[str, Any]] = None
_mdm_loaded = False
_hkcu_loaded = False
_lock = threading.Lock()


def startMdmSettingsLoad() -> None:
    """Begin loading MDM settings in the background."""
    def _load() -> None:
        global _mdm_cache, _mdm_loaded
        data = fireRawRead()
        with _lock:
            _mdm_cache = data
            _mdm_loaded = True

    t = threading.Thread(target=_load, daemon=True, name='mdm-settings-load')
    t.start()


def getMdmSettings() -> Optional[Dict[str, Any]]:
    """Return the cached MDM settings, loading them synchronously if not yet loaded."""
    global _mdm_cache, _mdm_loaded
    with _lock:
        if _mdm_loaded:
            return _mdm_cache
    # Force synchronous load if not ready
    data = fireRawRead()
    with _lock:
        _mdm_cache = data
        _mdm_loaded = True
    return data


def getHkcuSettings() -> Optional[Dict[str, Any]]:
    """Return the HKCU (per-user registry) MDM settings on Windows; None elsewhere."""
    import sys
    if sys.platform != 'win32':
        return None
    global _hkcu_cache, _hkcu_loaded
    with _lock:
        if _hkcu_loaded:
            return _hkcu_cache
    try:
        import subprocess
        from .constants import WINDOWS_REGISTRY_KEY_PATH_HKCU, WINDOWS_REGISTRY_VALUE_NAME
        import json
        result = subprocess.run(
            ['reg', 'query', WINDOWS_REGISTRY_KEY_PATH_HKCU, '/v', WINDOWS_REGISTRY_VALUE_NAME],
            capture_output=True, text=True, timeout=5
        )
        data = None
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if WINDOWS_REGISTRY_VALUE_NAME in line:
                    parts = line.strip().split(None, 2)
                    if len(parts) >= 3:
                        data = json.loads(parts[2].strip())
                        break
    except Exception:
        data = None
    with _lock:
        _hkcu_cache = data
        _hkcu_loaded = True
    return data


def resetMdmCache() -> None:
    """Reset MDM caches for testing."""
    global _mdm_cache, _hkcu_cache, _mdm_loaded, _hkcu_loaded
    with _lock:
        _mdm_cache = None
        _hkcu_cache = None
        _mdm_loaded = False
        _hkcu_loaded = False

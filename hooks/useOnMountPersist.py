"""On mount persist — mirrors src/hooks/useOnMountPersist.ts.

In Python, this persists values to a JSON file in the config directory on initialization.
Similar to React's useEffect hook with dependency tracking.
"""
from __future__ import annotations
from typing import Any, Optional
import json
from pathlib import Path
import os

# Persistent storage file
_PERSIST_DIR = Path(os.path.expanduser("~/.vivian_cli/persist"))
_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
_PERSIST_FILE = _PERSIST_DIR / "mounted_values.json"

_persisted_values: dict[str, Any] = {}
_initialized = False

def _load_persisted_values() -> None:
    """Load persisted values from disk."""
    global _persisted_values, _initialized
    if _PERSIST_FILE.exists():
        try:
            with open(_PERSIST_FILE, 'r') as f:
                _persisted_values = json.load(f)
        except (json.JSONDecodeError, IOError):
            _persisted_values = {}
    _initialized = True

def _save_persisted_values() -> None:
    """Save persisted values to disk."""
    _PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(_PERSIST_FILE, 'w') as f:
            json.dump(_persisted_values, f, indent=2, default=str)
    except IOError:
        pass  # Silently fail if we can't write

def useOnMountPersist(key: str, value: Any) -> Any:
    """Persist a value on mount and return the persisted value.
    
    On first mount, persists the provided value to disk. On subsequent mounts,
    returns the previously persisted value from disk.
    
    Args:
        key: Unique key for this persisted value
        value: Value to persist on first mount
        
    Returns:
        The persisted value (either newly stored or previously saved)
    """
    global _persisted_values, _initialized
    
    if not _initialized:
        _load_persisted_values()
    
    if key not in _persisted_values:
        # First mount - persist the value
        _persisted_values[key] = value
        _save_persisted_values()
    
    return _persisted_values.get(key, value)

def clear_persisted_value(key: str) -> None:
    """Clear a persisted value by key."""
    global _persisted_values
    if key in _persisted_values:
        del _persisted_values[key]
        _save_persisted_values()

def clear_all_persisted_values() -> None:
    """Clear all persisted values."""
    global _persisted_values
    _persisted_values = {}
    if _PERSIST_FILE.exists():
        _PERSIST_FILE.unlink()

use_on_mount_persist = useOnMountPersist

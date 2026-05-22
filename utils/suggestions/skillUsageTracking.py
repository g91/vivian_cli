"""Port of src/utils/suggestions/skillUsageTracking.ts - Skill usage scoring."""
from __future__ import annotations
from typing import Any, Dict, Optional
import time
import math
import threading
import json
import os

_HALF_LIFE_SECONDS = 7 * 24 * 3600  # 7 days
_DEBOUNCE_SECONDS = 60.0  # 60s debounce

# In-memory tracking: skill_name -> {'count': int, 'lastUsed': float}
_usage_data: Dict[str, Dict[str, Any]] = {}
_pending_write: Dict[str, Any] = {}
_debounce_timers: Dict[str, threading.Timer] = {}
_data_file: Optional[str] = None


def _get_data_file() -> str:
    global _data_file
    if _data_file:
        return _data_file
    config_dir = os.path.join(os.path.expanduser('~'), '.config', 'vivian')
    os.makedirs(config_dir, exist_ok=True)
    _data_file = os.path.join(config_dir, 'skill_usage.json')
    return _data_file


def _load_data() -> Dict[str, Dict[str, Any]]:
    """Load skill usage from disk, returning empty dict on any error."""
    try:
        with open(_get_data_file(), 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _ensure_loaded() -> None:
    """Lazily load data from disk into _usage_data."""
    if not _usage_data:
        loaded = _load_data()
        _usage_data.update(loaded)


def _persist(skill_name: str) -> None:
    """Write skill usage data to disk (called by debounce timer)."""
    try:
        with open(_get_data_file(), 'w') as f:
            json.dump(_usage_data, f)
    except OSError:
        pass
    _debounce_timers.pop(skill_name, None)


def record_skill_usage(skill_name: str) -> None:
    """Record a skill usage. Debounces writes to disk by 60s."""
    _ensure_loaded()
    existing = _usage_data.get(skill_name, {'count': 0, 'lastUsed': 0.0})
    _usage_data[skill_name] = {
        'count': existing['count'] + 1,
        'lastUsed': time.time(),
    }
    # Cancel existing debounce timer
    timer = _debounce_timers.get(skill_name)
    if timer:
        timer.cancel()
    new_timer = threading.Timer(_DEBOUNCE_SECONDS, _persist, args=[skill_name])
    new_timer.daemon = True
    new_timer.start()
    _debounce_timers[skill_name] = new_timer


recordSkillUsage = record_skill_usage


def get_skill_usage_score(skill_name: str) -> float:
    """Return a usage score using exponential decay (half-life = 7 days).
    
    score = usage_count * max(0.5^(age_seconds / half_life), 0.1)
    """
    _ensure_loaded()
    usage = _usage_data.get(skill_name)
    if not usage:
        return 0.0
    count = usage.get('count', 0)
    last_used = usage.get('lastUsed', 0.0)
    age_seconds = max(0.0, time.time() - last_used)
    decay = 0.5 ** (age_seconds / _HALF_LIFE_SECONDS)
    decay = max(decay, 0.1)
    return count * decay


getSkillUsageScore = get_skill_usage_score


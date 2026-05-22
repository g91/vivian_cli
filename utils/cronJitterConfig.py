"""
Port of src/utils/cronJitterConfig.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
from ..services.analytics.growthbook import getFeatureValue_CACHED_WITH_REFRESH
from .cronTasks import DEFAULT_CRON_JITTER_CONFIG


JITTER_CONFIG_REFRESH_MS = 60 * 1000
HALF_HOUR_MS = 30 * 60 * 1000
THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000


def getCronJitterConfig():
    """Read `tengu_kairos_cron_config` from GrowthBook, validate, fall back to
defaults on absent/malformed/out-of-bounds config. Called from check()
every tick via the `getJitterConfig` callback — cheap (synchronous cache
hit). Refresh window: JITTER_CONFIG_REFRESH_MS.

Exported so ops runbooks can point at a single function when documenting
the lever, and so tests can spy on it without mocking GrowthBook itself.

Pass this as `getJitterConfig` when calling createCronScheduler in REPL
contexts. Daemon/SDK callers omit getJitterConfig and get defaults."""
    raw = getFeatureValue_CACHED_WITH_REFRESH(
        'tengu_kairos_cron_config',
        DEFAULT_CRON_JITTER_CONFIG,
        JITTER_CONFIG_REFRESH_MS,
    )
    parsed = _validate_cron_jitter_config(raw)
    return parsed if parsed is not None else dict(DEFAULT_CRON_JITTER_CONFIG)


def _validate_cron_jitter_config(raw):
    if not isinstance(raw, dict):
        return None

    recurring_frac = raw.get('recurringFrac')
    recurring_cap_ms = raw.get('recurringCapMs')
    one_shot_max_ms = raw.get('oneShotMaxMs')
    one_shot_floor_ms = raw.get('oneShotFloorMs')
    one_shot_minute_mod = raw.get('oneShotMinuteMod')
    recurring_max_age_ms = raw.get(
        'recurringMaxAgeMs',
        DEFAULT_CRON_JITTER_CONFIG['recurringMaxAgeMs'],
    )

    if not _is_number_in_range(recurring_frac, 0, 1):
        return None
    if not _is_int_in_range(recurring_cap_ms, 0, HALF_HOUR_MS):
        return None
    if not _is_int_in_range(one_shot_max_ms, 0, HALF_HOUR_MS):
        return None
    if not _is_int_in_range(one_shot_floor_ms, 0, HALF_HOUR_MS):
        return None
    if not _is_int_in_range(one_shot_minute_mod, 1, 60):
        return None
    if not _is_int_in_range(recurring_max_age_ms, 0, THIRTY_DAYS_MS):
        return None
    if one_shot_floor_ms > one_shot_max_ms:
        return None

    return {
        'recurringFrac': float(recurring_frac),
        'recurringCapMs': int(recurring_cap_ms),
        'oneShotMaxMs': int(one_shot_max_ms),
        'oneShotFloorMs': int(one_shot_floor_ms),
        'oneShotMinuteMod': int(one_shot_minute_mod),
        'recurringMaxAgeMs': int(recurring_max_age_ms),
    }


def _is_int_in_range(value, minimum, maximum):
    return isinstance(value, int) and not isinstance(value, bool) and minimum <= value <= maximum


def _is_number_in_range(value, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return minimum <= float(value) <= maximum


get_cron_jitter_config = getCronJitterConfig


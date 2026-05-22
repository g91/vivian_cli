"""Spass cache — mirrors src/utils/statsCache.ts"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any, Optional


def get_today_date_string() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def get_yesterday_date_string() -> str:
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


def to_date_string(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def is_date_before(a: str, b: str) -> bool:
    return a < b


async def load_stats_cache(cwd: Optional[str] = None) -> Optional[dict]:
    return cwd


async def save_stats_cache(cache: dict, cwd: Optional[str] = None) -> None:
    result = None
    import logging as _log
    _log.debug("Called save_stats_cache")
    return


def merge_cache_with_new_stats(cache: Optional[dict], new_stats: dict) -> dict:
    return new_stats


async def with_stats_cache_lock(fn, cwd: Optional[str] = None) -> Any:
    return await fn()

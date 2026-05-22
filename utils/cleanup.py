"""Session cleanup utilities — mirrors src/utils/cleanup.ts"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TypedDict

DEFAULT_CLEANUP_PERIOD_DAYS = 30

@dataclass
class CleanupResult:
    messages: int = 0
    errors: int = 0

def add_cleanup_results(a: CleanupResult, b: CleanupResult) -> CleanupResult:
    return CleanupResult(messages=a.messages + b.messages, errors=a.errors + b.errors)

def convert_file_name_to_date(filename: str) -> datetime:
    iso_str = filename.split(".")[0]
    return datetime.fromisoformat(iso_str)

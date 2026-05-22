"""
passpasspass of src/utils/cron
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict


class CronFields(TypedDict):
    minute: list[int]
    hour: list[int]
    dayOfMonth: list[int]
    month: list[int]
    dayOfWeek: list[int]


class FieldRange(TypedDict):
    min: int
    max: int


FIELD_RANGES: tuple[FieldRange, ...] = (
    {"min": 0, "max": 59},
    {"min": 0, "max": 23},
    {"min": 1, "max": 31},
    {"min": 1, "max": 12},
    {"min": 0, "max": 6},
)

DAY_NAMES = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
]


def _cron_weekday(value: datetime) -> int:
    return (value.weekday() + 1) % 7


def _start_of_next_month(value: datetime) -> datetime:
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    return value.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)


def expandField(field, field_range):
    minimum = field_range["min"]
    maximum = field_range["max"]
    out: set[int] = set()

    for part in field.split(","):
        step_match = re.fullmatch(r"\*(?:/(\d+))?", part)
        if step_match:
            step = int(step_match.group(1) or "1")
            if step < 1:
                return None
            out.update(range(minimum, maximum + 1, step))
            continue

        range_match = re.fullmatch(r"(\d+)-(\d+)(?:/(\d+))?", part)
        if range_match:
            lo = int(range_match.group(1))
            hi = int(range_match.group(2))
            step = int(range_match.group(3) or "1")
            is_dow = minimum == 0 and maximum == 6
            effective_max = 7 if is_dow else maximum
            if lo > hi or step < 1 or lo < minimum or hi > effective_max:
                return None
            for item in range(lo, hi + 1, step):
                out.add(0 if is_dow and item == 7 else item)
            continue

        if re.fullmatch(r"\d+", part):
            value = int(part)
            if minimum == 0 and maximum == 6 and value == 7:
                value = 0
            if value < minimum or value > maximum:
                return None
            out.add(value)
            continue

        return None

    if not out:
        return None
    return sorted(out)


def parseCronExpression(expr):
    """Parse a 5-field cron expression into expanded number arrays."""
    parts = re.split(r"\s+", expr.strip())
    if len(parts) != 5:
        return None

    expanded: list[list[int]] = []
    for index, part in enumerate(parts):
        result = expandField(part, FIELD_RANGES[index])
        if result is None:
            return None
        expanded.append(result)

    return {
        "minute": expanded[0],
        "hour": expanded[1],
        "dayOfMonth": expanded[2],
        "month": expanded[3],
        "dayOfWeek": expanded[4],
    }


def computeNextCronRun(fields, from_):
    """Compute the next Date strictly after `from` that matches the cron fields,"""
    minute_set = set(fields["minute"])
    hour_set = set(fields["hour"])
    dom_set = set(fields["dayOfMonth"])
    month_set = set(fields["month"])
    dow_set = set(fields["dayOfWeek"])

    dom_wild = len(fields["dayOfMonth"]) == 31
    dow_wild = len(fields["dayOfWeek"]) == 7

    current = from_.replace(second=0, microsecond=0) + timedelta(minutes=1)
    max_iter = 366 * 24 * 60
    for _ in range(max_iter):
        if current.month not in month_set:
            current = _start_of_next_month(current)
            continue

        dom = current.day
        dow = _cron_weekday(current)
        if dom_wild and dow_wild:
            day_matches = True
        elif dom_wild:
            day_matches = dow in dow_set
        elif dow_wild:
            day_matches = dom in dom_set
        else:
            day_matches = dom in dom_set or dow in dow_set

        if not day_matches:
            current = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            continue

        if current.hour not in hour_set:
            current = (current + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            continue

        if current.minute not in minute_set:
            current = current + timedelta(minutes=1)
            continue

        return current

    return None


def formatLocalTime(minute, hour):
    formatted = datetime(2000, 1, 1, hour, minute).strftime("%I:%M %p")
    return formatted.lstrip("0")


def formatUtcTimeAsLocal(minute, hour):
    current_utc = datetime.now(timezone.utc)
    utc_value = current_utc.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return utc_value.astimezone().strftime("%I:%M %p %Z").lstrip("0")


def cronToHuman(cron, opts=None):
    utc = bool((opts or {}).get("utc", False))
    parts = re.split(r"\s+", cron.strip())
    if len(parts) != 5:
        return cron

    minute, hour, day_of_month, month, day_of_week = parts

    every_min_match = re.fullmatch(r"\*/(\d+)", minute)
    if every_min_match and hour == "*" and day_of_month == "*" and month == "*" and day_of_week == "*":
        count = int(every_min_match.group(1))
        return "Every minute" if count == 1 else f"Every {count} minutes"

    if re.fullmatch(r"\d+", minute) and hour == "*" and day_of_month == "*" and month == "*" and day_of_week == "*":
        minute_value = int(minute)
        if minute_value == 0:
            return "Every hour"
        return f"Every hour at :{minute_value:02d}"

    every_hour_match = re.fullmatch(r"\*/(\d+)", hour)
    if re.fullmatch(r"\d+", minute) and every_hour_match and day_of_month == "*" and month == "*" and day_of_week == "*":
        count = int(every_hour_match.group(1))
        minute_value = int(minute)
        suffix = "" if minute_value == 0 else f" at :{minute_value:02d}"
        return f"Every hour{suffix}" if count == 1 else f"Every {count} hours{suffix}"

    if not re.fullmatch(r"\d+", minute) or not re.fullmatch(r"\d+", hour):
        return cron

    minute_value = int(minute)
    hour_value = int(hour)
    formatter = formatUtcTimeAsLocal if utc else formatLocalTime

    if day_of_month == "*" and month == "*" and day_of_week == "*":
        return f"Every day at {formatter(minute_value, hour_value)}"

    if day_of_month == "*" and month == "*" and re.fullmatch(r"\d", day_of_week):
        day_index = int(day_of_week) % 7
        if utc:
            ref = datetime.now(timezone.utc)
            days_to_add = (day_index - _cron_weekday(ref) + 7) % 7
            ref = ref + timedelta(days=days_to_add)
            ref = ref.replace(hour=hour_value, minute=minute_value, second=0, microsecond=0)
            day_name = DAY_NAMES[_cron_weekday(ref.astimezone())]
        else:
            day_name = DAY_NAMES[day_index]
        return f"Every {day_name} at {formatter(minute_value, hour_value)}"

    if day_of_month == "*" and month == "*" and day_of_week == "1-5":
        return f"Weekdays at {formatter(minute_value, hour_value)}"

    return cron


parse_cron_expression = parseCronExpression
compute_next_cron_run = computeNextCronRun
cron_to_human = cronToHuman
format_local_time = formatLocalTime
format_utc_time_as_local = formatUtcTimeAsLocal


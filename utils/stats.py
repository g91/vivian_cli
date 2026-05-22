"""Port of src/utils/stats.ts."""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from .debug import logForDebugging
from .envUtils import get_vivian_config_home_dir
from .messages import SYNTHETIC_MODEL


DailyActivity = Dict[str, Any]
DailyModelTokens = Dict[str, Any]
StreakInfo = Dict[str, Any]
SessionStats = Dict[str, Any]
vivianCodeStats = Dict[str, Any]
ProcessedStats = Dict[str, Any]
ProcessOptions = Dict[str, Any]
StatsDateRange = str
_BATCH_SIZE = 20
_SHOT_COUNT_REGEX = re.compile(r"(\d+)-shotted by")
_TRANSCRIPT_MESSAGE_TYPES = {"user", "assistant", "attachment", "system", "progress"}
_SHELL_TOOL_NAMES = {"Bash", "bash", "PowerShell", "powershell"}


def _to_date_string(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _is_date_before(left: str, right: str) -> bool:
    return left < right


def _get_projects_dir() -> str:
    return str(Path(get_vivian_config_home_dir()) / "projects")


def _is_transcript_message(entry: Any) -> bool:
    return isinstance(entry, dict) and entry.get("type") in _TRANSCRIPT_MESSAGE_TYPES


def _read_jsonl_file(file_path: str) -> List[dict[str, Any]]:
    entries: List[dict[str, Any]] = []
    with open(file_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except Exception:
                continue
            if isinstance(parsed, dict):
                entries.append(parsed)
    return entries


def _merge_model_usage(existing: dict[str, Any], usage: dict[str, Any]) -> dict[str, Any]:
    if not existing:
        return {
            "inputTokens": usage.get("input_tokens", 0),
            "outputTokens": usage.get("output_tokens", 0),
            "cacheReadInputTokens": usage.get("cache_read_input_tokens", 0),
            "cacheCreationInputTokens": usage.get("cache_creation_input_tokens", 0),
            "webSearchRequests": usage.get("web_search_requests", 0),
            "costUSD": usage.get("cost_usd", 0),
            "contextWindow": usage.get("context_window", 0),
            "maxOutputTokens": usage.get("max_output_tokens", 0),
        }
    existing["inputTokens"] += usage.get("input_tokens", 0)
    existing["outputTokens"] += usage.get("output_tokens", 0)
    existing["cacheReadInputTokens"] += usage.get("cache_read_input_tokens", 0)
    existing["cacheCreationInputTokens"] += usage.get("cache_creation_input_tokens", 0)
    existing["webSearchRequests"] += usage.get("web_search_requests", 0)
    existing["costUSD"] += usage.get("cost_usd", 0)
    existing["contextWindow"] = max(existing.get("contextWindow", 0), usage.get("context_window", 0))
    existing["maxOutputTokens"] = max(existing.get("maxOutputTokens", 0), usage.get("max_output_tokens", 0))
    return existing


async def processSessionFiles(sessionFiles, options={}):
    """Process session files and extract stats."""
    from_date = options.get("fromDate")
    to_date = options.get("toDate")
    daily_activity_map: dict[str, DailyActivity] = {}
    daily_model_tokens_map: dict[str, dict[str, int]] = {}
    sessions: List[SessionStats] = []
    hour_counts: dict[int, int] = defaultdict(int)
    total_messages = 0
    total_speculation_time_saved_ms = 0
    model_usage_agg: dict[str, dict[str, Any]] = {}
    shot_distribution_map: dict[int, int] = defaultdict(int)
    sessions_with_shot_count: set[str] = set()

    for index in range(0, len(sessionFiles), _BATCH_SIZE):
        batch = sessionFiles[index : index + _BATCH_SIZE]
        for session_file in batch:
            try:
                if from_date:
                    try:
                        stat = os.stat(session_file)
                        modified_date = _to_date_string(datetime.fromtimestamp(stat.st_mtime))
                        if _is_date_before(modified_date, from_date):
                            continue
                        if stat.st_size > 65536:
                            start_date = await readSessionStartDate(session_file)
                            if start_date and _is_date_before(start_date, from_date):
                                continue
                    except OSError:
                        pass
                entries = _read_jsonl_file(session_file)
            except Exception as error:
                logForDebugging(f"Failed to read session file {session_file}: {error}")
                continue

            messages = [entry for entry in entries if _is_transcript_message(entry)]
            for entry in entries:
                if isinstance(entry, dict) and entry.get("type") == "speculation-accept":
                    total_speculation_time_saved_ms += int(entry.get("timeSavedMs", 0) or 0)
            if not messages:
                continue

            is_subagent_file = f"{os.sep}subagents{os.sep}" in session_file
            session_id = Path(session_file).stem
            parent_session_id = Path(session_file).parents[1].name if is_subagent_file else session_id
            if parent_session_id not in sessions_with_shot_count:
                shot_count = extractShotCountFromMessages(messages)
                if shot_count is not None:
                    sessions_with_shot_count.add(parent_session_id)
                    shot_distribution_map[shot_count] += 1

            main_messages = messages if is_subagent_file else [message for message in messages if not message.get("isSidechain")]
            if not main_messages:
                continue

            first_raw = main_messages[0].get("timestamp")
            last_raw = main_messages[-1].get("timestamp")
            if not isinstance(first_raw, str) or not isinstance(last_raw, str):
                continue
            try:
                first_timestamp = datetime.fromisoformat(first_raw.replace("Z", "+00:00"))
                last_timestamp = datetime.fromisoformat(last_raw.replace("Z", "+00:00"))
            except ValueError:
                continue

            date_key = _to_date_string(first_timestamp)
            if from_date and _is_date_before(date_key, from_date):
                continue
            if to_date and _is_date_before(to_date, date_key):
                continue

            existing = daily_activity_map.get(date_key) or {
                "date": date_key,
                "messageCount": 0,
                "sessionCount": 0,
                "toolCallCount": 0,
            }

            if not is_subagent_file:
                sessions.append(
                    {
                        "sessionId": session_id,
                        "duration": int((last_timestamp - first_timestamp).total_seconds() * 1000),
                        "messageCount": len(main_messages),
                        "timestamp": first_raw,
                    }
                )
                total_messages += len(main_messages)
                existing["sessionCount"] += 1
                existing["messageCount"] += len(main_messages)
                hour_counts[first_timestamp.hour] += 1

            if not is_subagent_file or date_key in daily_activity_map:
                daily_activity_map[date_key] = existing

            for message in main_messages:
                if message.get("type") != "assistant":
                    continue
                content = ((message.get("message") or {}).get("content"))
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            activity = daily_activity_map.get(date_key)
                            if activity is not None:
                                activity["toolCallCount"] += 1

                usage = ((message.get("message") or {}).get("usage"))
                model = ((message.get("message") or {}).get("model")) or "unknown"
                if not isinstance(usage, dict) or model == SYNTHETIC_MODEL:
                    continue

                model_usage_agg[model] = _merge_model_usage(model_usage_agg.get(model, {}), usage)
                total_tokens = int(usage.get("input_tokens", 0) or 0) + int(usage.get("output_tokens", 0) or 0)
                if total_tokens > 0:
                    day_tokens = daily_model_tokens_map.get(date_key) or {}
                    day_tokens[model] = day_tokens.get(model, 0) + total_tokens
                    daily_model_tokens_map[date_key] = day_tokens

    return {
        "dailyActivity": sorted(daily_activity_map.values(), key=lambda item: item["date"]),
        "dailyModelTokens": sorted(
            ({"date": date, "tokensByModel": tokens} for date, tokens in daily_model_tokens_map.items()),
            key=lambda item: item["date"],
        ),
        "modelUsage": model_usage_agg,
        "sessionStats": sessions,
        "hourCounts": dict(hour_counts),
        "totalMessages": total_messages,
        "totalSpeculationTimeSavedMs": total_speculation_time_saved_ms,
        "shotDistribution": dict(shot_distribution_map),
    }


async def getAllSessionFiles():
    """Get all session files from all project directories."""
    projects_dir = _get_projects_dir()
    if not os.path.isdir(projects_dir):
        return []

    session_files: List[str] = []
    try:
        for project_entry in os.scandir(projects_dir):
            if not project_entry.is_dir():
                continue
            try:
                session_dirs: List[str] = []
                for entry in os.scandir(project_entry.path):
                    if entry.is_file() and entry.name.endswith(".jsonl"):
                        session_files.append(entry.path)
                    elif entry.is_dir():
                        session_dirs.append(entry.path)
                for session_dir in session_dirs:
                    subagents_dir = os.path.join(session_dir, "subagents")
                    if not os.path.isdir(subagents_dir):
                        continue
                    for subagent_entry in os.scandir(subagents_dir):
                        if subagent_entry.is_file() and subagent_entry.name.endswith(".jsonl") and subagent_entry.name.startswith("agent-"):
                            session_files.append(subagent_entry.path)
            except Exception as error:
                logForDebugging(f"Failed to read project directory {project_entry.path}: {error}")
    except FileNotFoundError:
        return []
    return session_files


def cacheToStats(cache, todayStats):
    """Convert a PersistedStatsCache to vivianCodeStats by computing derived fields."""
    if cache and isinstance(cache, dict):
        combined = dict(cache)
        if todayStats:
            combined.update(todayStats)
        return processedStatsTovivianCodeStats(combined)
    return processedStatsTovivianCodeStats(todayStats or getEmptyStats())


async def aggregatevivianCodeStats():
    """Aggregates stats from all vivian Code sessions across all projects."""
    all_session_files = await getAllSessionFiles()
    if not all_session_files:
        return getEmptyStats()
    stats = await processSessionFiles(all_session_files, {})
    return processedStatsTovivianCodeStats(stats)


async def aggregatevivianCodeStatsForRange(range):
    """Aggregates stats for a specific date range."""
    if range == "all":
        return await aggregatevivianCodeStats()
    all_session_files = await getAllSessionFiles()
    if not all_session_files:
        return getEmptyStats()
    days_back = 7 if range == "7d" else 30
    from_date = datetime.now() - timedelta(days=days_back - 1)
    stats = await processSessionFiles(all_session_files, {"fromDate": _to_date_string(from_date)})
    return processedStatsTovivianCodeStats(stats)


def processedStatsTovivianCodeStats(stats):
    """Convert ProcessedStats to vivianCodeStats."""
    daily_activity_sorted = sorted(list(stats.get("dailyActivity", [])), key=lambda item: item["date"])
    daily_model_tokens_sorted = sorted(list(stats.get("dailyModelTokens", [])), key=lambda item: item["date"])
    streaks = calculateStreaks(daily_activity_sorted)

    longest_session = None
    for session in stats.get("sessionStats", []):
        if longest_session is None or session.get("duration", 0) > longest_session.get("duration", 0):
            longest_session = session

    first_session_date = None
    last_session_date = None
    for session in stats.get("sessionStats", []):
        timestamp = session.get("timestamp")
        if not timestamp:
            continue
        if first_session_date is None or timestamp < first_session_date:
            first_session_date = timestamp
        if last_session_date is None or timestamp > last_session_date:
            last_session_date = timestamp

    peak_activity_day = max(daily_activity_sorted, key=lambda item: item.get("messageCount", 0)).get("date") if daily_activity_sorted else None
    peak_activity_hour = int(max(stats.get("hourCounts", {}).items(), key=lambda item: item[1])[0]) if stats.get("hourCounts") else None

    total_days = 0
    if first_session_date and last_session_date:
        first_dt = datetime.fromisoformat(str(first_session_date).replace("Z", "+00:00"))
        last_dt = datetime.fromisoformat(str(last_session_date).replace("Z", "+00:00"))
        total_days = (last_dt.date() - first_dt.date()).days + 1

    result = {
        "totalSessions": len(stats.get("sessionStats", [])),
        "totalMessages": stats.get("totalMessages", 0),
        "totalDays": total_days,
        "activeDays": len(daily_activity_sorted),
        "streaks": streaks,
        "dailyActivity": daily_activity_sorted,
        "dailyModelTokens": daily_model_tokens_sorted,
        "longestSession": longest_session,
        "modelUsage": stats.get("modelUsage", {}),
        "firstSessionDate": first_session_date,
        "lastSessionDate": last_session_date,
        "peakActivityDay": peak_activity_day,
        "peakActivityHour": peak_activity_hour,
        "totalSpeculationTimeSavedMs": stats.get("totalSpeculationTimeSavedMs", 0),
    }
    shot_distribution = stats.get("shotDistribution") or {}
    if shot_distribution:
        result["shotDistribution"] = shot_distribution
        total_with_shots = sum(shot_distribution.values())
        result["oneShotRate"] = round((shot_distribution.get(1, 0) / total_with_shots) * 100) if total_with_shots > 0 else 0
    return result


def getNextDay(dateStr):
    """Get the next day after a given date string (YYYY-MM-DD format)."""
    return _to_date_string(datetime.fromisoformat(dateStr) + timedelta(days=1))


def calculateStreaks(dailyActivity):
    if not dailyActivity:
        return {
            "currentStreak": 0,
            "longestStreak": 0,
            "currentStreakStart": None,
            "longestStreakStart": None,
            "longestStreakEnd": None,
        }

    today = datetime.now().date()
    active_dates = {item["date"] for item in dailyActivity}
    current_streak = 0
    current_streak_start = None
    check_date = today
    while True:
        date_str = check_date.strftime("%Y-%m-%d")
        if date_str not in active_dates:
            break
        current_streak += 1
        current_streak_start = date_str
        check_date -= timedelta(days=1)

    sorted_dates = sorted(active_dates)
    longest_streak = 0
    longest_streak_start = None
    longest_streak_end = None
    temp_streak = 0
    temp_start = None
    previous = None
    for date_str in sorted_dates:
        current = datetime.fromisoformat(date_str).date()
        if previous and (current - previous).days == 1:
            temp_streak += 1
        else:
            temp_streak = 1
            temp_start = date_str
        if temp_streak > longest_streak:
            longest_streak = temp_streak
            longest_streak_start = temp_start
            longest_streak_end = date_str
        previous = current

    return {
        "currentStreak": current_streak,
        "longestStreak": longest_streak,
        "currentStreakStart": current_streak_start,
        "longestStreakStart": longest_streak_start,
        "longestStreakEnd": longest_streak_end,
    }


def extractShotCountFromMessages(messages):
    """Extract the shot count from PR attribution text in a `gh pr create` Bash call."""
    for message in messages:
        if message.get("type") != "assistant":
            continue
        content = ((message.get("message") or {}).get("content"))
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            if block.get("name") not in _SHELL_TOOL_NAMES:
                continue
            command = ((block.get("input") or {}).get("command"))
            if not isinstance(command, str):
                continue
            match = _SHOT_COUNT_REGEX.search(command)
            if match:
                return int(match.group(1))
    return None


async def readSessionStartDate(filePath):
    """Peeks at the head of a session file to get the session start date."""
    try:
        with open(filePath, "rb") as handle:
            head = handle.read(4096).decode("utf-8", errors="ignore")
    except Exception:
        return None
    last_newline = head.rfind("\n")
    if last_newline < 0:
        return None
    for line in head[:last_newline].splitlines():
        if not line:
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue
        if not isinstance(entry, dict) or entry.get("type") not in _TRANSCRIPT_MESSAGE_TYPES:
            continue
        if entry.get("isSidechain") is True:
            continue
        timestamp = entry.get("timestamp")
        if not isinstance(timestamp, str):
            return None
        try:
            date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return None
        return _to_date_string(date)
    return None


def getEmptyStats():
    return {
        "totalSessions": 0,
        "totalMessages": 0,
        "totalDays": 0,
        "activeDays": 0,
        "streaks": {
            "currentStreak": 0,
            "longestStreak": 0,
            "currentStreakStart": None,
            "longestStreakStart": None,
            "longestStreakEnd": None,
        },
        "dailyActivity": [],
        "dailyModelTokens": [],
        "longestSession": None,
        "modelUsage": {},
        "firstSessionDate": None,
        "lastSessionDate": None,
        "peakActivityDay": None,
        "peakActivityHour": None,
        "totalSpeculationTimeSavedMs": 0,
    }


process_session_files = processSessionFiles
get_all_session_files = getAllSessionFiles
cache_to_stats = cacheToStats
aggregate_vivian_code_stats = aggregatevivianCodeStats
aggregate_vivian_code_stats_for_range = aggregatevivianCodeStatsForRange
processed_stats_to_vivian_code_stats = processedStatsTovivianCodeStats
get_next_day = getNextDay
extract_shot_count_from_messages = extractShotCountFromMessages
read_session_start_date = readSessionStartDate
get_empty_stats = getEmptyStats


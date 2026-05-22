"""
Port of src/utils/attribution.ts
"""
from __future__ import annotations

from typing import Any, Dict, List
import os
import json

from ..bootstrap.state import getClientType, getSessionId
from ..constants.product import PRODUCT_URL, getRemoteSessionUrl, isRemoteSessionLocal
from .debug import logForDebugging


AttributionTexts = Dict[str, Any]
_TERMINAL_OUTPUT_TAGS = ("local-command-stdout", "local-command-stderr", "bash-stdout", "bash-stderr")
_MEMORY_ACCESS_TOOL_NAMES = {"Read", "Edit", "Write", "Grep", "Glob", "FileRead", "FileEdit", "FileWrite"}


def _get_initial_settings() -> dict[str, Any]:
    try:
        from .settings.settings import getSettingsForSource

        merged: dict[str, Any] = {}
        for source in ("userSettings", "projectSettings", "localSettings", "flagSettings", "policySettings"):
            value = getSettingsForSource(source)
            if isinstance(value, dict):
                merged.update(value)
        return merged
    except Exception:
        return {}


def _is_undercover() -> bool:
    if os.environ.get("USER_TYPE") != "ant":
        return False
    raw = os.environ.get("vivian_CODE_UNDERCOVER", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _get_transcript_path() -> str | None:
    try:
        from .sessionStorage import getTranscriptPathForSession

        path = getTranscriptPathForSession(getSessionId())
        return path if isinstance(path, str) else None
    except Exception:
        return None


def _sanitize_model_name(model_name: str) -> str:
    return model_name.replace("-202", "").replace("-20", "")


def getAttributionTexts():
    """Returns attribution text for commits and PRs based on user settings."""
    if _is_undercover():
        return {"commit": "", "pr": ""}

    if getClientType() == "remote":
        remote_session_id = os.environ.get("vivian_CODE_REMOTE_SESSION_ID")
        if remote_session_id:
            ingress_url = os.environ.get("SESSION_INGRESS_URL", "")
            if not isRemoteSessionLocal(remote_session_id, ingress_url):
                session_url = getRemoteSessionUrl(remote_session_id, ingress_url)
                return {"commit": session_url, "pr": session_url}
        return {"commit": "", "pr": ""}

    default_attribution = f"Generated with [vivian Code]({PRODUCT_URL})"
    model_name = os.environ.get("vivian_MODEL_NAME") or os.environ.get("vivian_CODE_MODEL") or "vivian Opus 4.6"
    default_commit = f"Co-Authored-By: {model_name} <noreply@anthropic.com>"
    settings = _get_initial_settings()
    attribution = settings.get("attribution") or {}
    if isinstance(attribution, dict):
        return {
            "commit": attribution.get("commit", default_commit),
            "pr": attribution.get("pr", default_attribution),
        }
    if settings.get("includeCoAuthoredBy") is False:
        return {"commit": "", "pr": ""}
    return {"commit": default_commit, "pr": default_attribution}


def isTerminalOutput(content):
    """Check if a message content string is terminal output rather than a user prompt."""
    if not isinstance(content, str):
        return False
    return any(f"<{tag}>" in content for tag in _TERMINAL_OUTPUT_TAGS)


def countUserPromptsInMessages(messages=None):
    """Count user messages with visible text content in a list of non-sidechain messages."""
    count = 0
    for message in messages or []:
        if message.get("type") != "user":
            continue
        content = ((message.get("message") or {}).get("content"))
        has_user_text = False
        if isinstance(content, str):
            has_user_text = bool(content.strip()) and not isTerminalOutput(content)
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                block_type = block.get("type")
                if block_type in {"image", "document"}:
                    has_user_text = True
                    break
                if block_type == "text" and isinstance(block.get("text"), str) and not isTerminalOutput(block["text"]):
                    has_user_text = True
                    break
        if has_user_text:
            count += 1
    return count


def countUserPromptsFromEntries(entries):
    """Count non-sidechain user messages in transcript entries."""
    non_sidechain = [entry for entry in entries or [] if entry.get("type") == "user" and not entry.get("isSidechain")]
    return countUserPromptsInMessages(non_sidechain)


async def getPRAttributionData(appState):
    """Get full attribution data from the provided AppState's attribution state."""
    attribution = (appState or {}).get("attribution")
    if not attribution:
        return None
    file_states = attribution.get("fileStates") or {}
    tracked_files = list(file_states.keys()) if isinstance(file_states, dict) else list(file_states)
    if not tracked_files:
        return None
    try:
        from .commitAttribution import calculateCommitAttribution

        result = await calculateCommitAttribution([attribution], tracked_files)
        return result if isinstance(result, dict) else None
    except Exception as error:
        logForDebugging(f"PR Attribution: failed to calculate commit attribution: {error}")
        return None


def countMemoryFileAccessFromEntries(entries):
    """Count memory file accesses in transcript entries."""
    count = 0
    for entry in entries or []:
        if entry.get("type") != "assistant":
            continue
        content = ((entry.get("message") or {}).get("content"))
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            if block.get("name") not in _MEMORY_ACCESS_TOOL_NAMES:
                continue
            tool_input = block.get("input") or {}
            pathish = " ".join(str(tool_input.get(key, "")) for key in ("file_path", "path", "pattern", "query"))
            if ".vivian" in pathish or "memories" in pathish or "memory" in pathish:
                count += 1
    return count


async def getTranscriptStats():
    """Read session transcript entries and compute prompt count and memory access"""
    file_path = _get_transcript_path()
    if not file_path or not os.path.exists(file_path):
        return {"promptCount": 0, "memoryAccessCount": 0}
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            entries = []
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
        last_boundary_idx = -1
        for index, entry in enumerate(entries):
            if entry.get("type") == "system" and entry.get("subtype") == "compact_boundary":
                last_boundary_idx = index
        post_boundary = entries[last_boundary_idx + 1 :] if last_boundary_idx >= 0 else entries
        return {
            "promptCount": countUserPromptsFromEntries(post_boundary),
            "memoryAccessCount": countMemoryFileAccessFromEntries(post_boundary),
        }
    except Exception as error:
        logForDebugging(f"PR Attribution: transcript stats failed: {error}")
        return {"promptCount": 0, "memoryAccessCount": 0}


async def getEnhancedPRAttribution(getAppState=None):
    """Get enhanced PR attribution text with vivian contribution stats."""
    if _is_undercover():
        return ""

    if getClientType() == "remote":
        remote_session_id = os.environ.get("vivian_CODE_REMOTE_SESSION_ID")
        if remote_session_id:
            ingress_url = os.environ.get("SESSION_INGRESS_URL", "")
            if not isRemoteSessionLocal(remote_session_id, ingress_url):
                return getRemoteSessionUrl(remote_session_id, ingress_url)
        return ""

    settings = _get_initial_settings()
    attribution = settings.get("attribution") or {}
    if isinstance(attribution, dict) and attribution.get("pr"):
        return attribution["pr"]
    if settings.get("includeCoAuthoredBy") is False:
        return ""

    default_attribution = f"Generated with [vivian Code]({PRODUCT_URL})"
    app_state = getAppState() if callable(getAppState) else {}
    attribution_data = await getPRAttributionData(app_state)
    transcript_stats = await getTranscriptStats()
    summary = attribution_data.get("summary") if isinstance(attribution_data, dict) else None
    vivian_percent = ((summary or {}).get("vivianPercent")) or 0
    prompt_count = transcript_stats["promptCount"]
    memory_access_count = transcript_stats["memoryAccessCount"]
    raw_model_name = os.environ.get("vivian_MODEL_NAME") or os.environ.get("vivian_CODE_MODEL") or "vivian-opus-4-6"
    short_model_name = _sanitize_model_name(raw_model_name)

    if vivian_percent == 0 and prompt_count == 0 and memory_access_count == 0:
        return default_attribution

    mem_suffix = ""
    if memory_access_count > 0:
        noun = "memory" if memory_access_count == 1 else "memories"
        mem_suffix = f", {memory_access_count} {noun} recalled"
    summary = f"Generated with [vivian Code]({PRODUCT_URL}) ({vivian_percent}% {prompt_count}-shotted by {short_model_name}{mem_suffix})"
    logForDebugging(f"PR Attribution: returning summary: {summary}")
    return summary


get_attribution_texts = getAttributionTexts
is_terminal_output = isTerminalOutput
count_user_prompts_in_messages = countUserPromptsInMessages
count_user_prompts_from_entries = countUserPromptsFromEntries
get_pr_attribution_data = getPRAttributionData
count_memory_file_access_from_entries = countMemoryFileAccessFromEntries
get_transcript_stats = getTranscriptStats
get_enhanced_pr_attribution = getEnhancedPRAttribution


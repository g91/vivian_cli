"""Port of src/utils/plans.ts."""

from __future__ import annotations

import json
import os
import uuid
from functools import lru_cache
from pathlib import Path
from shutil import copyfile
from typing import Any, Optional

from ..bootstrap.state import getPlanSlugCache, getSessionId
from ..constants.tools import EXIT_PLAN_MODE_TOOL_NAME
from .cwd import get_cwd
from .debug import logForDebugging
from .envUtils import get_vivian_config_home_dir
from .errors import isENOENT
from .file import getDisplayPath
from .filePersistence.outputsScanner import getEnvironmentKind
from .log import logError
from .settings.settings import getInitialSettings
from .words import generate_word_slug


MAX_SLUG_RETRIES = 10


@lru_cache(maxsize=1)
def getPlansDirectory() -> str:
    """Return the directory where plan files are stored for this session."""
    settings = getInitialSettings() or {}
    settings_dir = settings.get("plansDirectory") if isinstance(settings, dict) else None
    default_dir = os.path.join(get_vivian_config_home_dir(), "plans")

    plans_path = default_dir
    if isinstance(settings_dir, str) and settings_dir.strip():
        cwd = os.path.realpath(get_cwd())
        resolved = os.path.realpath(os.path.join(cwd, settings_dir))
        try:
            within_project = os.path.commonpath([cwd, resolved]) == cwd
        except ValueError:
            within_project = False
        if within_project:
            plans_path = resolved
        else:
            logError(Exception(f"plansDirectory must be within project root: {settings_dir}"))

    try:
        os.makedirs(plans_path, exist_ok=True)
    except Exception as error:
        logError(error)
    return plans_path


def getPlanSlug(sessionId: Optional[str] = None) -> str:
    """Get or lazily create the cached slug for a session's plan file."""
    session_id = sessionId or getSessionId()
    cache = getPlanSlugCache()
    slug = cache.get(session_id)
    if slug:
        return slug

    plans_dir = getPlansDirectory()
    for _ in range(MAX_SLUG_RETRIES):
        candidate = generate_word_slug()
        candidate_path = os.path.join(plans_dir, f"{candidate}.md")
        if not os.path.exists(candidate_path):
            slug = candidate
            break
    if not slug:
        slug = f"plan-{uuid.uuid4().hex[:8]}"
    cache[session_id] = slug
    return slug


def setPlanSlug(sessionId: str, slug: str) -> None:
    """Set the cached plan slug for a session."""
    getPlanSlugCache()[sessionId] = slug


def clearPlanSlug(sessionId: Optional[str] = None) -> None:
    """Clear the cached plan slug for one session."""
    session_id = sessionId or getSessionId()
    getPlanSlugCache().pop(session_id, None)


def clearAllPlanSlugs() -> None:
    """Clear all cached plan slugs."""
    getPlanSlugCache().clear()


def getPlanFilePath(agentId: Optional[str] = None) -> str:
    """Return the on-disk path for the current session's plan file."""
    plan_slug = getPlanSlug(getSessionId())
    if not agentId:
        return os.path.join(getPlansDirectory(), f"{plan_slug}.md")
    return os.path.join(getPlansDirectory(), f"{plan_slug}-agent-{agentId}.md")


def getPlan(agentId: Optional[str] = None) -> Optional[str]:
    """Read the current session's plan text from disk if present."""
    file_path = getPlanFilePath(agentId)
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            return handle.read()
    except Exception as error:
        if isENOENT(error):
            return None
        logError(error)
        return None


def getSlugFromLog(log: dict[str, Any]) -> Optional[str]:
    """Extract the plan slug from a transcript log."""
    for message in log.get("messages") or []:
        if isinstance(message, dict) and isinstance(message.get("slug"), str):
            return message["slug"]
    return None


async def copyPlanForResume(log: dict[str, Any], targetSessionId: Optional[str] = None) -> bool:
    """Restore the cached plan slug for a resumed session and recover the file if needed."""
    slug = getSlugFromLog(log)
    if not slug:
        return False

    session_id = targetSessionId or getSessionId()
    setPlanSlug(session_id, slug)
    plan_path = os.path.join(getPlansDirectory(), f"{slug}.md")

    try:
        with open(plan_path, "r", encoding="utf-8"):
            return True
    except Exception as error:
        if not isENOENT(error):
            logError(error)
            return False

    if getEnvironmentKind() is None:
        return False

    logForDebugging(f"Plan file missing during resume: {plan_path}. Attempting recovery.")
    snapshot_plan = findFileSnapshotEntry(log.get("messages") or [], "plan")
    recovered = None
    if snapshot_plan and snapshot_plan.get("content"):
        recovered = str(snapshot_plan["content"])
        logForDebugging(
            f"Plan recovered from file snapshot, {len(recovered)} chars",
            level="info",
        )
    else:
        recovered = recoverPlanFromMessages(log)
        if recovered:
            logForDebugging(
                f"Plan recovered from message history, {len(recovered)} chars",
                level="info",
            )

    if not recovered:
        logForDebugging(
            "Plan file recovery failed: no file snapshot or plan content found in message history"
        )
        return False

    try:
        with open(plan_path, "w", encoding="utf-8") as handle:
            handle.write(recovered)
        return True
    except Exception as error:
        logError(error)
        return False


async def copyPlanForFork(log: dict[str, Any], targetSessionId: str) -> bool:
    """Copy the current plan into a new slug for a forked session."""
    original_slug = getSlugFromLog(log)
    if not original_slug:
        return False

    original_plan_path = os.path.join(getPlansDirectory(), f"{original_slug}.md")
    new_slug = getPlanSlug(targetSessionId)
    new_plan_path = os.path.join(getPlansDirectory(), f"{new_slug}.md")
    try:
        copyfile(original_plan_path, new_plan_path)
        return True
    except Exception as error:
        if isENOENT(error):
            return False
        logError(error)
        return False


def recoverPlanFromMessages(log: dict[str, Any]) -> Optional[str]:
    """Recover plan text from assistant/user/attachment transcript entries."""
    messages = log.get("messages") or []
    for message in reversed(messages):
        if not isinstance(message, dict):
            continue

        if message.get("type") == "assistant":
            content = (message.get("message") or {}).get("content")
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use" and block.get("name") == EXIT_PLAN_MODE_TOOL_NAME:
                        input_data = block.get("input") or {}
                        plan = input_data.get("plan") if isinstance(input_data, dict) else None
                        if isinstance(plan, str) and plan:
                            return plan

        if message.get("type") == "user":
            plan_content = message.get("planContent")
            if isinstance(plan_content, str) and plan_content:
                return plan_content

        if message.get("type") == "attachment":
            attachment = message.get("attachment") or {}
            if isinstance(attachment, dict) and attachment.get("type") == "plan_file_reference":
                plan_content = attachment.get("planContent")
                if isinstance(plan_content, str) and plan_content:
                    return plan_content
    return None


def findFileSnapshotEntry(messages: list[Any], key: str) -> Optional[dict[str, str]]:
    """Find a keyed file entry in the latest file snapshot system message."""
    for message in reversed(messages):
        if not isinstance(message, dict):
            continue
        if message.get("type") != "system" or message.get("subtype") != "file_snapshot":
            continue
        snapshot_files = message.get("snapshotFiles") or []
        for entry in snapshot_files:
            if isinstance(entry, dict) and entry.get("key") == key:
                return entry
        return None
    return None


async def persistFileSnapshotIfRemote() -> None:
    """Append a remote-only file snapshot message to the current transcript."""
    if getEnvironmentKind() is None:
        return

    plan = getPlan()
    if not plan:
        return

    message = {
        "type": "system",
        "subtype": "file_snapshot",
        "content": "File snapshot",
        "level": "info",
        "isMeta": True,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        "uuid": str(uuid.uuid4()),
        "snapshotFiles": [
            {
                "key": "plan",
                "path": getPlanFilePath(),
                "displayPath": getDisplayPath(getPlanFilePath()),
                "content": plan,
            }
        ],
    }

    try:
        from .sessionStorage import getTranscriptPath

        transcript_path = Path(getTranscriptPath())
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        with transcript_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message, ensure_ascii=False) + "\n")
    except Exception as error:
        logError(error)


get_plans_directory = getPlansDirectory
get_plan_slug = getPlanSlug
set_plan_slug = setPlanSlug
clear_plan_slug = clearPlanSlug
clear_all_plan_slugs = clearAllPlanSlugs
get_plan_file_path = getPlanFilePath
get_plan = getPlan
get_slug_from_log = getSlugFromLog
copy_plan_for_resume = copyPlanForResume
copy_plan_for_fork = copyPlanForFork
recover_plan_from_messages = recoverPlanFromMessages
find_file_snapshot_entry = findFileSnapshotEntry
persist_file_snapshot_if_remote = persistFileSnapshotIfRemote


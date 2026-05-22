"""
Port of src/utils/plugins/officialMarketplaceStartupCheck.ts

Auto-install logic for the official Anthropic marketplace.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

from ..config import getGlobalConfig, saveGlobalConfig
from ..debug import logForDebugging
from ..envUtils import is_env_truthy
from ..errors import errorMessage
from ..log import logError
from .gitAvailability import checkGitAvailable, markGitUnavailable
from .marketplaceHelpers import isSourceAllowedByPolicy
from .marketplaceManager import (
    addMarketplaceSource,
    getMarketplacesCacheDir,
    loadKnownMarketplacesConfig,
    saveKnownMarketplacesConfig,
)
from .officialMarketplace import OFFICIAL_MARKETPLACE_NAME, OFFICIAL_MARKETPLACE_SOURCE
from .officialMarketplaceGcs import fetchOfficialMarketplaceFromGcs

OfficialMarketplaceSkipReason = str
OfficialMarketplaceCheckResult = Dict[str, Any]

RETRY_CONFIG = {
    "MAX_ATTEMPTS": 10,
    "INITIAL_DELAY_MS": 60 * 60 * 1000,
    "BACKOFF_MULTIPLIER": 2,
    "MAX_DELAY_MS": 7 * 24 * 60 * 60 * 1000,
}


def isOfficialMarketplaceAutoInstallDisabled() -> bool:
    return is_env_truthy(os.environ.get("vivian_CODE_DISABLE_OFFICIAL_MARKETPLACE_AUTOINSTALL"))


def _calculate_next_retry_delay(retry_count: int) -> int:
    delay = RETRY_CONFIG["INITIAL_DELAY_MS"] * (RETRY_CONFIG["BACKOFF_MULTIPLIER"] ** retry_count)
    return min(delay, RETRY_CONFIG["MAX_DELAY_MS"])


def _should_retry_installation(config: Dict[str, Any]) -> bool:
    if not config.get("officialMarketplaceAutoInstallAttempted"):
        return True
    if config.get("officialMarketplaceAutoInstalled"):
        return False
    fail_reason = config.get("officialMarketplaceAutoInstallFailReason")
    retry_count = config.get("officialMarketplaceAutoInstallRetryCount", 0)
    next_retry_time = config.get("officialMarketplaceAutoInstallNextRetryTime")
    now = int(time.time() * 1000)

    if retry_count >= RETRY_CONFIG["MAX_ATTEMPTS"]:
        return False
    if fail_reason == "policy_blocked":
        return False
    if next_retry_time and now < next_retry_time:
        return False
    return fail_reason in ("unknown", "git_unavailable", "gcs_unavailable", None)


async def checkAndInstallOfficialMarketplace() -> OfficialMarketplaceCheckResult:
    config = getGlobalConfig()

    if not _should_retry_installation(config):
        reason = config.get("officialMarketplaceAutoInstallFailReason", "already_attempted")
        return {"installed": False, "skipped": True, "reason": reason}

    try:
        if isOfficialMarketplaceAutoInstallDisabled():
            saveGlobalConfig(lambda c: {**c, "officialMarketplaceAutoInstallAttempted": True, "officialMarketplaceAutoInstalled": False, "officialMarketplaceAutoInstallFailReason": "policy_blocked"})
            return {"installed": False, "skipped": True, "reason": "policy_blocked"}

        known = await loadKnownMarketplacesConfig()
        if OFFICIAL_MARKETPLACE_NAME in known:
            saveGlobalConfig(lambda c: {**c, "officialMarketplaceAutoInstallAttempted": True, "officialMarketplaceAutoInstalled": True})
            return {"installed": False, "skipped": True, "reason": "already_installed"}

        if not isSourceAllowedByPolicy(OFFICIAL_MARKETPLACE_SOURCE):
            saveGlobalConfig(lambda c: {**c, "officialMarketplaceAutoInstallAttempted": True, "officialMarketplaceAutoInstalled": False, "officialMarketplaceAutoInstallFailReason": "policy_blocked"})
            return {"installed": False, "skipped": True, "reason": "policy_blocked"}

        cache_dir = getMarketplacesCacheDir()
        install_location = os.path.join(cache_dir, OFFICIAL_MARKETPLACE_NAME)
        gcs_sha = await fetchOfficialMarketplaceFromGcs(install_location, cache_dir)

        if gcs_sha is not None:
            known = await loadKnownMarketplacesConfig()
            known[OFFICIAL_MARKETPLACE_NAME] = {"source": OFFICIAL_MARKETPLACE_SOURCE, "installLocation": install_location, "lastUpdated": ""}
            await saveKnownMarketplacesConfig(known)
            saveGlobalConfig(lambda c: {**c, "officialMarketplaceAutoInstallAttempted": True, "officialMarketplaceAutoInstalled": True})
            return {"installed": True, "skipped": False}

        git_available = await checkGitAvailable()
        if not git_available:
            retry_count = config.get("officialMarketplaceAutoInstallRetryCount", 0) + 1
            now = int(time.time() * 1000)
            next_retry = now + _calculate_next_retry_delay(retry_count)
            saveGlobalConfig(lambda c: {**c, "officialMarketplaceAutoInstallAttempted": True, "officialMarketplaceAutoInstalled": False, "officialMarketplaceAutoInstallFailReason": "git_unavailable", "officialMarketplaceAutoInstallRetryCount": retry_count, "officialMarketplaceAutoInstallNextRetryTime": next_retry})
            return {"installed": False, "skipped": True, "reason": "git_unavailable"}

        await addMarketplaceSource(OFFICIAL_MARKETPLACE_SOURCE)
        saveGlobalConfig(lambda c: {**c, "officialMarketplaceAutoInstallAttempted": True, "officialMarketplaceAutoInstalled": True})
        return {"installed": True, "skipped": False}

    except Exception as e:
        msg = str(e)
        if "xcrun: error:" in msg:
            markGitUnavailable()
            return {"installed": False, "skipped": True, "reason": "git_unavailable"}

        retry_count = config.get("officialMarketplaceAutoInstallRetryCount", 0) + 1
        now = int(time.time() * 1000)
        next_retry = now + _calculate_next_retry_delay(retry_count)
        saveGlobalConfig(lambda c: {**c, "officialMarketplaceAutoInstallAttempted": True, "officialMarketplaceAutoInstalled": False, "officialMarketplaceAutoInstallFailReason": "unknown", "officialMarketplaceAutoInstallRetryCount": retry_count, "officialMarketplaceAutoInstallNextRetryTime": next_retry})
        return {"installed": False, "skipped": True, "reason": "unknown"}


calculateNextRetryDelay = _calculate_next_retry_delay
shouldRetryInstallation = _should_retry_installation


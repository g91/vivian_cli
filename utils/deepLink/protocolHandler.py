"""Port of src/utils/deepLink/protocolHandler.ts."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from ..debug import logForDebugging
from ..githubRepoPathMapping import filterExistingPaths, getKnownPathsForRepo
from .banner import readLastFetchTime
from .parseDeepLink import parseDeepLink
from .registerProtocol import MACOS_BUNDLE_ID
from .terminalLauncher import launchInTerminal


async def handleDeepLinkUri(uri: str) -> int:
    logForDebugging(f"Handling deep link URI: {uri}")
    try:
        action = parseDeepLink(uri)
    except Exception as error:
        print(f"Deep link error: {error}", file=sys.stderr)
        return 1

    logForDebugging(f"Parsed deep link action: {json.dumps(action.__dict__, sort_keys=True)}")
    resolved = await resolveCwd(action.__dict__)
    cwd = resolved["cwd"]
    resolved_repo = resolved.get("resolvedRepo")
    last_fetch = await readLastFetchTime(cwd) if resolved_repo else None
    launched = await launchInTerminal(
        sys.executable,
        {
            "query": action.query,
            "cwd": cwd,
            "repo": resolved_repo,
            "lastFetchMs": int(last_fetch.timestamp() * 1000) if last_fetch else None,
        },
    )
    if not launched:
        print(
            "Failed to open a terminal. Make sure a supported terminal emulator is installed.",
            file=sys.stderr,
        )
        return 1
    return 0


async def handleUrlSchemeLaunch():
    if os.environ.get("__CFBundleIdentifier") != MACOS_BUNDLE_ID:
        return None
    url = os.environ.get("vivian_DEEP_LINK_URL")
    if not url:
        return None
    try:
        return await handleDeepLinkUri(url)
    except Exception:
        return None


async def resolveCwd(action=None):
    action = action or {}
    if action.get("cwd"):
        return {"cwd": str(action["cwd"])}
    if action.get("repo"):
        known = getKnownPathsForRepo(action["repo"])
        existing = await filterExistingPaths(known)
        if existing:
            logForDebugging(f"Resolved repo {action['repo']} → {existing[0]}")
            return {"cwd": existing[0], "resolvedRepo": str(action["repo"])}
        logForDebugging(f"No local clone found for repo {action['repo']}, falling back to home")
    return {"cwd": str(Path.home())}


handle_deep_link_uri = handleDeepLinkUri
handle_url_scheme_launch = handleUrlSchemeLaunch
resolve_cwd = resolveCwd


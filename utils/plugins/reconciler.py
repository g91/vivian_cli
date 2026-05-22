"""
Port of src/utils/plugins/reconciler.ts

Marketplace reconciler — makes known_marketplaces.json consistent with declared intent.
"""
from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional

from ...bootstrap.state import getOriginalCwd
from ..debug import logForDebugging
from ..errors import errorMessage
from ..file import pathExists
from ..git import findCanonicalGitRoot
from ..log import logError
from .marketplaceManager import (
    addMarketplaceSource,
    getDeclaredMarketplaces,
    loadKnownMarketplacesConfig,
)
from .schemas import isLocalMarketplaceSource, KnownMarketplacesFile, MarketplaceSource

MarketplaceDiff = Dict[str, Any]
ReconcileOptions = Dict[str, Any]
ReconcileProgressEvent = Any
ReconcileResult = Dict[str, Any]


def diffMarketplaces(
    declared: Dict[str, Any],
    materialized: KnownMarketplacesFile,
    project_root: Optional[str] = None,
) -> MarketplaceDiff:
    """Compare declared intent against materialized state."""
    missing: List[str] = []
    source_changed: List[Dict[str, Any]] = []
    up_to_date: List[str] = []

    for name, intent in declared.items():
        state = materialized.get(name)
        normalized = _normalize_source(intent.get("source", {}), project_root)

        if not state:
            missing.append(name)
        elif intent.get("sourceIsFallback"):
            up_to_date.append(name)
        elif normalized != state.get("source"):
            source_changed.append({"name": name, "declaredSource": normalized, "materializedSource": state["source"]})
        else:
            up_to_date.append(name)

    return {"missing": missing, "sourceChanged": source_changed, "upToDate": up_to_date}


async def reconcileMarketplaces(opts: Optional[Dict[str, Any]] = None) -> ReconcileResult:
    """Make known_marketplaces.json consistent with declared intent."""
    if opts is None:
        opts = {}

    declared = getDeclaredMarketplaces()
    if not declared:
        return {"installed": [], "updated": [], "failed": [], "upToDate": [], "skipped": []}

    try:
        materialized = await loadKnownMarketplacesConfig()
    except Exception as e:
        logError(e)
        materialized = {}

    diff = diffMarketplaces(declared, materialized, getOriginalCwd())

    work: List[Dict[str, Any]] = []
    for name in diff["missing"]:
        work.append({"name": name, "source": _normalize_source(declared[name]["source"]), "action": "install"})
    for item in diff["sourceChanged"]:
        work.append({"name": item["name"], "source": item["declaredSource"], "action": "update"})

    skip_fn = opts.get("skip")
    skipped: List[str] = []
    to_process: List[Dict[str, Any]] = []

    for item in work:
        if skip_fn and skip_fn(item["name"], item["source"]):
            skipped.append(item["name"])
            continue
        if item["action"] == "update" and isLocalMarketplaceSource(item["source"]) and not await pathExists(item["source"]["path"]):
            skipped.append(item["name"])
            continue
        to_process.append(item)

    if not to_process:
        return {"installed": [], "updated": [], "failed": [], "upToDate": diff["upToDate"], "skipped": skipped}

    installed: List[str] = []
    updated: List[str] = []
    failed: List[Dict[str, str]] = []

    for item in to_process:
        try:
            await addMarketplaceSource(item["source"])
            if item["action"] == "install":
                installed.append(item["name"])
            else:
                updated.append(item["name"])
        except Exception as e:
            failed.append({"name": item["name"], "error": errorMessage(e)})

    return {"installed": installed, "updated": updated, "failed": failed, "upToDate": diff["upToDate"], "skipped": skipped}


def _normalize_source(source: Dict[str, Any], project_root: Optional[str] = None) -> Dict[str, Any]:
    """Resolve relative directory/file paths for stable comparison."""
    if source.get("source") in ("directory", "file") and not os.path.isabs(source.get("path", "")):
        base = project_root or getOriginalCwd()
        canonical = findCanonicalGitRoot(base)
        return {**source, "path": os.path.realpath(os.path.join(canonical or base, source["path"]))}
    return source


normalizeSource = _normalize_source


"""Port of src/utils/plugins/officialMarketplaceGcs.ts.

Fetch the official marketplace from a GCS mirror.
"""
from __future__ import annotations

import os
import re
import shutil
import zipfile
from typing import Any, Optional

from ..debug import logForDebugging
from ..errors import errorMessage, getErrnoCode

GCS_BASE = "https://api-vivian.d0a.net/vivian-code-releases/plugins/vivian-plugins-official"
ARC_PREFIX = "marketplaces/vivian-plugins-official/"

KNOWN_FS_CODES = {"ENOSPC", "EACCES", "EPERM", "EXDEV", "EBUSY", "ENOENT", "ENOTDIR", "EROFS", "EMFILE", "ENAMETOOLONG"}


async def fetchOfficialMarketplaceFromGcs(
    install_location: str,
    marketplaces_cache_dir: str,
) -> Optional[str]:
    """Fetch the official marketplace from GCS and extract to installLocation."""
    cache_dir = os.path.realpath(marketplaces_cache_dir)
    resolved_loc = os.path.realpath(install_location)
    sep = os.sep

    if resolved_loc != cache_dir and not resolved_loc.startswith(cache_dir + sep):
        logForDebugging(f"fetchOfficialMarketplaceFromGcs: refusing path outside cache dir: {install_location}", level="error")
        return None

    try:
        import httpx

        # 1. Latest pointer
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{GCS_BASE}/latest")
            sha = resp.text.strip()

        if not sha:
            raise ValueError("latest pointer returned empty body")

        # 2. Sentinel check
        sentinel_path = os.path.join(install_location, ".gcs-sha")
        try:
            with open(sentinel_path, "r") as f:
                current_sha = f.read().strip()
            if current_sha == sha:
                return sha
        except FileNotFoundError:
            pass

        # 3. Download and extract
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(f"{GCS_BASE}/{sha}.zip")
            zip_buf = resp.content

        staging = f"{install_location}.staging"
        shutil.rmtree(staging, ignore_errors=True)
        os.makedirs(staging, exist_ok=True)

        import io
        with zipfile.ZipFile(io.BytesIO(zip_buf), "r") as zf:
            for info in zf.infolist():
                if not info.filename.startswith(ARC_PREFIX) or info.is_dir():
                    continue
                rel = info.filename[len(ARC_PREFIX):]
                if not rel:
                    continue
                dest = os.path.join(staging, rel)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with zf.open(info) as src, open(dest, "wb") as dst:
                    dst.write(src.read())

        with open(os.path.join(staging, ".gcs-sha"), "w") as f:
            f.write(sha)

        shutil.rmtree(install_location, ignore_errors=True)
        os.rename(staging, install_location)

        return sha
    except Exception as e:
        logForDebugging(f"Official marketplace GCS fetch failed: {errorMessage(e)}", level="warn")
        return None


def classifyGcsError(e: Any) -> str:
    """Classify a GCS fetch error into a stable telemetry bucket."""
    msg = str(e)
    if "timeout" in msg.lower() or "ECONNABORTED" in msg:
        return "timeout"
    if re.search(r"http_\d{3}", msg):
        return re.search(r"http_(\d{3})", msg).group(0)
    if "network" in msg.lower():
        return "network"
    code = getErrnoCode(e)
    if code and re.match(r"^E[A-Z]+$", code) and not code.startswith("ERR_"):
        return f"fs_{code}" if code in KNOWN_FS_CODES else "fs_other"
    if "unzip" in msg.lower() or "zip" in msg.lower():
        return "zip_parse"
    if "empty body" in msg.lower():
        return "empty_latest"
    return "other"


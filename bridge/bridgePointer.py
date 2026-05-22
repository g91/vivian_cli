"""Port of src/bridge/bridgePointer.ts

Crash-recovery pointer for Remote Control sessions.
Written after a bridge session is created, refreshed periodically,
and cleared on clean shutdown.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, Literal, Optional


BRIDGE_POINTER_TTL_MS = 4 * 60 * 60 * 1000  # 4 hours

BridgePointerSource = Literal["standalone", "repl"]

MAX_WORKTREE_FANOUT = 50


class BridgePointer:
    def __init__(self, session_id: str, environment_id: str, source: BridgePointerSource) -> None:
        self.sessionId = session_id
        self.environmentId = environment_id
        self.source = source

    def to_dict(self) -> Dict[str, str]:
        return {
            "sessionId": self.sessionId,
            "environmentId": self.environmentId,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, str]) -> "BridgePointer":
        if not all(k in d for k in ("sessionId", "environmentId", "source")):
            raise ValueError(f"Missing required keys in bridge pointer: {d}")
        if d["source"] not in ("standalone", "repl"):
            raise ValueError(f"Invalid source: {d['source']}")
        return cls(d["sessionId"], d["environmentId"], d["source"])  # type: ignore[arg-type]


def _get_projects_dir() -> str:
    try:
        from ..utils.session_storage_portable import get_projects_dir
        return get_projects_dir()
    except Exception:
        home = os.path.expanduser("~")
        return os.path.join(home, ".vivian", "projects")


def _sanitize_path(p: str) -> str:
    try:
        from ..utils.session_storage_portable import sanitize_path
        return sanitize_path(p)
    except Exception:
        return p.replace("/", "__").replace("\\", "__").lstrip("__")


def getBridgePointerPath(directory: str) -> str:
    return os.path.join(_get_projects_dir(), _sanitize_path(directory), "bridge-pointer.json")


async def writeBridgePointer(directory: str, pointer: BridgePointer) -> None:
    """Write the pointer file. Best-effort — logs and swallows on error."""
    path = getBridgePointerPath(directory)
    try:
        import aiofiles
        os.makedirs(os.path.dirname(path), exist_ok=True)
        async with aiofiles.open(path, "w") as f:
            await f.write(json.dumps(pointer.to_dict()))
    except ImportError:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            Path(path).write_text(json.dumps(pointer.to_dict()))
        except Exception as e:
            try:
                from ..utils.debug import log_for_debugging
                log_for_debugging(f"[bridge:pointer] write failed: {e}", level="warn")
            except Exception:
                pass
    except Exception as e:
        try:
            from ..utils.debug import log_for_debugging
            log_for_debugging(f"[bridge:pointer] write failed: {e}", level="warn")
        except Exception:
            pass


async def readBridgePointer(directory: str) -> Optional[Dict]:
    """
    Read the pointer and its age. Returns None on any failure:
    missing file, bad JSON, schema mismatch, or stale (>4h).
    """
    path = getBridgePointerPath(directory)
    try:
        stat = os.stat(path)
        mtime_ms = int(stat.st_mtime * 1000)
        raw = Path(path).read_text()
    except Exception:
        return None

    try:
        data = json.loads(raw)
        pointer = BridgePointer.from_dict(data)
    except Exception:
        try:
            from ..utils.debug import log_for_debugging
            log_for_debugging(f"[bridge:pointer] invalid schema, clearing: {path}")
        except Exception:
            pass
        await clearBridgePointer(directory)
        return None

    age_ms = max(0, int(time.time() * 1000) - mtime_ms)
    if age_ms > BRIDGE_POINTER_TTL_MS:
        try:
            from ..utils.debug import log_for_debugging
            log_for_debugging(f"[bridge:pointer] stale (>4h mtime), clearing: {path}")
        except Exception:
            pass
        await clearBridgePointer(directory)
        return None

    return {**pointer.to_dict(), "ageMs": age_ms}


async def readBridgePointerAcrossWorktrees(directory: str) -> Optional[Dict]:
    """
    Worktree-aware read for --continue. Fans out across git worktree siblings
    to find the freshest pointer.
    """
    here = await readBridgePointer(directory)
    if here:
        return {"pointer": here, "dir": directory}

    # Fanout: scan worktree siblings
    try:
        from ..utils.get_worktree_paths_portable import get_worktree_paths_portable
        worktrees = await get_worktree_paths_portable(directory)
    except Exception:
        return None

    if len(worktrees) <= 1:
        return None
    if len(worktrees) > MAX_WORKTREE_FANOUT:
        return None

    dir_key = _sanitize_path(directory)
    candidates = [wt for wt in worktrees if _sanitize_path(wt) != dir_key]

    import asyncio
    results = await asyncio.gather(
        *[readBridgePointer(wt) for wt in candidates],
        return_exceptions=True,
    )

    best: Optional[Dict] = None
    best_dir: Optional[str] = None
    best_age = float("inf")

    for wt, result in zip(candidates, results):
        if isinstance(result, dict) and result.get("ageMs", float("inf")) < best_age:
            best = result
            best_dir = wt
            best_age = result["ageMs"]

    if best is None:
        return None
    return {"pointer": best, "dir": best_dir}


async def clearBridgePointer(directory: str) -> None:
    """Delete the bridge pointer file. Best-effort."""
    path = getBridgePointerPath(directory)
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
    except Exception:
        pass

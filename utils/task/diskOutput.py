"""Task disk output helpers mirroring src/utils/task/diskOutput.ts."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from ...bootstrap.state import getOriginalCwd, getSessionId
from ..errors import get_errno_code
from ..log import logError
from ..permissions.filesystem import getvivianTempDir
from ..readFileInRange import readFileInRange
from ..sessionStorage import sanitizePath

DEFAULT_MAX_READ_BYTES = 8 * 1024 * 1024
MAX_TASK_OUTPUT_BYTES = 5 * 1024 * 1024 * 1024
MAX_TASK_OUTPUT_BYTES_DISPLAY = "5GB"

_taskOutputDir: str | None = None
_pendingOps: set[asyncio.Task[Any]] = set()
outputs: dict[str, "DiskTaskOutput"] = {}


def getProjectTempDir() -> str:
    return str(Path(getvivianTempDir()) / sanitizePath(getOriginalCwd()))


def getTaskOutputDir():
    global _taskOutputDir
    if _taskOutputDir is None:
        _taskOutputDir = str(Path(getProjectTempDir()) / str(getSessionId()) / "tasks")
    return _taskOutputDir


def _resetTaskOutputDirForTest():
    global _taskOutputDir
    _taskOutputDir = None


async def ensureOutputDir():
    Path(getTaskOutputDir()).mkdir(parents=True, exist_ok=True)


def getTaskOutputPath(taskId):
    return str(Path(getTaskOutputDir()) / f"{taskId}.output")


def track(p):
    if not asyncio.iscoroutine(p):
        return p
    try:
        task = asyncio.create_task(p)
    except RuntimeError:
        return p
    _pendingOps.add(task)

    def _done(_task):
        _pendingOps.discard(_task)

    task.add_done_callback(_done)
    return task


class DiskTaskOutput:
    """Queued async writer for a single task output file."""

    def __init__(self, taskId: str):
        self._path = getTaskOutputPath(taskId)
        self._queue: list[str] = []
        self._bytes_written = 0
        self._capped = False
        self._flush_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    def append(self, content: str) -> None:
        if self._capped:
            return
        self._bytes_written += len(content.encode("utf-8"))
        if self._bytes_written > MAX_TASK_OUTPUT_BYTES:
            self._capped = True
            self._queue.append(
                f"\n[output truncated: exceeded {MAX_TASK_OUTPUT_BYTES_DISPLAY} disk cap]\n"
            )
        else:
            self._queue.append(content)
        if self._flush_task is None or self._flush_task.done():
            scheduled = track(self._drain())
            if asyncio.iscoroutine(scheduled):
                asyncio.run(scheduled)
                self._flush_task = None
            else:
                self._flush_task = scheduled

    async def flush(self) -> None:
        if self._flush_task is not None:
            await asyncio.shield(self._flush_task)

    def cancel(self) -> None:
        self._queue.clear()

    async def _drain(self) -> None:
        try:
            while self._queue:
                async with self._lock:
                    if not self._queue:
                        break
                    chunk = "".join(self._queue)
                    self._queue.clear()
                    await ensureOutputDir()
                    await asyncio.to_thread(_append_text, self._path, chunk)
        except Exception as error:
            logError(error)
            if self._queue:
                try:
                    async with self._lock:
                        if self._queue:
                            chunk = "".join(self._queue)
                            self._queue.clear()
                            await ensureOutputDir()
                            await asyncio.to_thread(_append_text, self._path, chunk)
                except Exception as retry_error:
                    logError(retry_error)


def _append_text(path: str, content: str) -> None:
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(content)


def getOrCreateOutput(taskId):
    output = outputs.get(taskId)
    if output is None:
        output = DiskTaskOutput(taskId)
        outputs[taskId] = output
    return output


def appendTaskOutput(taskId, content):
    getOrCreateOutput(taskId).append(content)


async def flushTaskOutput(taskId):
    output = outputs.get(taskId)
    if output is not None:
        await output.flush()


def evictTaskOutput(taskId):
    async def _evict() -> None:
        output = outputs.get(taskId)
        if output is not None:
            await output.flush()
            outputs.pop(taskId, None)

    return track(_evict())


async def getTaskOutputDelta(taskId, fromOffset, maxBytes=DEFAULT_MAX_READ_BYTES):
    try:
        result = await readFileInRange(
            getTaskOutputPath(taskId),
            offset=0,
            max_lines=None,
            max_bytes=maxBytes,
            options={"truncateOnByteLimit": True},
        )
        content = result.get("content", "")
        encoded = content.encode("utf-8")
        if fromOffset >= len(encoded):
            return {"content": "", "newOffset": fromOffset}
        delta_bytes = encoded[fromOffset:fromOffset + maxBytes]
        delta = delta_bytes.decode("utf-8", errors="replace")
        return {"content": delta, "newOffset": fromOffset + len(delta_bytes)}
    except Exception as error:
        if get_errno_code(error) == "ENOENT":
            return {"content": "", "newOffset": fromOffset}
        logError(error)
        return {"content": "", "newOffset": fromOffset}


async def getTaskOutput(taskId, maxBytes=DEFAULT_MAX_READ_BYTES):
    try:
        content, bytes_total = await asyncio.to_thread(_read_task_tail, getTaskOutputPath(taskId), maxBytes)
        bytes_read = len(content.encode("utf-8"))
        if bytes_total > bytes_read:
            omitted_kb = round((bytes_total - bytes_read) / 1024)
            return f"[{omitted_kb}KB of earlier output omitted]\n{content}"
        return content
    except Exception as error:
        if get_errno_code(error) == "ENOENT":
            return ""
        logError(error)
        return ""


async def getTaskOutputSize(taskId):
    try:
        return os.path.getsize(getTaskOutputPath(taskId))
    except Exception as error:
        if get_errno_code(error) == "ENOENT":
            return 0
        logError(error)
        return 0


async def cleanupTaskOutput(taskId):
    output = outputs.pop(taskId, None)
    if output is not None:
        output.cancel()
    try:
        await asyncio.to_thread(os.unlink, getTaskOutputPath(taskId))
    except Exception as error:
        if get_errno_code(error) != "ENOENT":
            logError(error)


def initTaskOutput(taskId):
    async def _init() -> str:
        await ensureOutputDir()
        output_path = getTaskOutputPath(taskId)
        def _create() -> None:
            with open(output_path, "x", encoding="utf-8"):
                pass
        await asyncio.to_thread(_create)
        return output_path

    return track(_init())


def initTaskOutputAsSymlink(taskId, targetPath):
    async def _init_symlink() -> str:
        try:
            await ensureOutputDir()
            output_path = getTaskOutputPath(taskId)

            def _link() -> None:
                try:
                    os.symlink(targetPath, output_path)
                except FileExistsError:
                    os.unlink(output_path)
                    os.symlink(targetPath, output_path)

            await asyncio.to_thread(_link)
            return output_path
        except Exception as error:
            logError(error)
            return await initTaskOutput(taskId)

    return track(_init_symlink())


async def _clearOutputsForTest():
    for output in outputs.values():
        output.cancel()
    while _pendingOps:
        await asyncio.gather(*list(_pendingOps), return_exceptions=True)
    outputs.clear()


def _read_task_tail(path: str, max_bytes: int) -> tuple[str, int]:
    with open(path, "rb") as handle:
        handle.seek(0, os.SEEK_END)
        total = handle.tell()
        read_size = min(total, max_bytes)
        handle.seek(max(total - read_size, 0), os.SEEK_SET)
        data = handle.read(read_size)
    return data.decode("utf-8", errors="replace"), total


get_project_temp_dir = getProjectTempDir
get_task_output_dir = getTaskOutputDir
reset_task_output_dir_for_test = _resetTaskOutputDirForTest
ensure_output_dir = ensureOutputDir
get_task_output_path = getTaskOutputPath
clear_outputs_for_test = _clearOutputsForTest
get_or_create_output = getOrCreateOutput
append_task_output = appendTaskOutput
flush_task_output = flushTaskOutput
evict_task_output = evictTaskOutput
get_task_output_delta = getTaskOutputDelta
get_task_output = getTaskOutput
get_task_output_size = getTaskOutputSize
cleanup_task_output = cleanupTaskOutput
init_task_output = initTaskOutput
init_task_output_as_symlink = initTaskOutputAsSymlink

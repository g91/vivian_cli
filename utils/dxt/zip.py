"""Port of src/utils/dxt/zip.ts"""
from __future__ import annotations
import io
import os
import struct
import zipfile
from typing import Any, Dict, Optional

LIMITS = {
    "MAX_FILE_SIZE": 512 * 1024 * 1024,
    "MAX_TOTAL_SIZE": 1024 * 1024 * 1024,
    "MAX_FILE_COUNT": 100000,
    "MAX_COMPRESSION_RATIO": 50,
    "MIN_COMPRESSION_RATIO": 0.5,
}

ZipValidationState = Dict[str, Any]
ZipFileMetadata = Dict[str, Any]
FileValidationResult = Dict[str, Any]


def isPathSafe(filePath: str) -> bool:
    """Validates a file path to prevent path traversal attacks."""
    parts = filePath.replace("\\", "/").split("/")
    if ".." in parts:
        return False
    normalized = os.path.normpath(filePath)
    if os.path.isabs(normalized):
        return False
    if filePath.startswith("/") or filePath.startswith("\\"):
        return False
    return True


def validateZipFile(file: Dict, state: Dict) -> Dict:
    """Validates a single file during zip extraction."""
    state["fileCount"] = state.get("fileCount", 0) + 1
    error = None

    if state["fileCount"] > LIMITS["MAX_FILE_COUNT"]:
        error = (
            f"Archive contains too many files: {state['fileCount']} "
            f"(max: {LIMITS['MAX_FILE_COUNT']})"
        )
    if error is None and not isPathSafe(file["name"]):
        error = (
            f"Unsafe file path detected: {file['name']!r}. "
            "Path traversal or absolute paths are not allowed."
        )
    file_size = file.get("originalSize", 0) or 0
    if error is None and file_size > LIMITS["MAX_FILE_SIZE"]:
        error = (
            f"File {file['name']!r} is too large: "
            f"{round(file_size/1024/1024)}MB "
            f"(max: {round(LIMITS['MAX_FILE_SIZE']/1024/1024)}MB)"
        )
    state["totalUncompressedSize"] = state.get("totalUncompressedSize", 0) + file_size
    if error is None and state["totalUncompressedSize"] > LIMITS["MAX_TOTAL_SIZE"]:
        error = (
            f"Archive total size is too large: "
            f"{round(state['totalUncompressedSize']/1024/1024)}MB "
            f"(max: {round(LIMITS['MAX_TOTAL_SIZE']/1024/1024)}MB)"
        )
    compressed_size = state.get("compressedSize", 1) or 1
    current_ratio = state["totalUncompressedSize"] / compressed_size
    if error is None and current_ratio > LIMITS["MAX_COMPRESSION_RATIO"]:
        error = (
            f"Suspicious compression ratio detected: {current_ratio:.1f}:1 "
            f"(max: {LIMITS['MAX_COMPRESSION_RATIO']}:1). This may be a zip bomb."
        )
    return {"isValid": False, "error": error} if error else {"isValid": True}


async def unzipFile(zipData: bytes) -> Dict[str, bytes]:
    """Unzips data from bytes and returns contents as file paths mapped to bytes."""
    compressed_size = len(zipData)
    state = {
        "fileCount": 0,
        "totalUncompressedSize": 0,
        "compressedSize": compressed_size,
        "errors": [],
    }
    result: Dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(zipData), "r") as zf:
            for info in zf.infolist():
                file_meta = {"name": info.filename, "originalSize": info.file_size}
                validation = validateZipFile(file_meta, state)
                if not validation["isValid"]:
                    raise ValueError(validation["error"])
                if not info.filename.endswith("/"):
                    result[info.filename] = zf.read(info.filename)
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Invalid zip file: {exc}")
    try:
        from vivian_cli.utils.debug import logForDebugging
        logForDebugging(
            f"Zip extraction completed: {state['fileCount']} files, "
            f"{round(state['totalUncompressedSize']/1024)}KB uncompressed"
        )
    except Exception:
        pass
    return result


def parseZipModes(data: bytes) -> Dict[str, int]:
    """Parse Unix file modes from a zip central directory.

    Returns name to mode for Unix-created entries (versionMadeBy high byte == 3).
    ZIP64 not handled — returns empty dict for archives >4GB or >65535 entries.
    """
    buf = data
    modes: Dict[str, int] = {}
    min_eocd = max(0, len(buf) - 22 - 0xFFFF)
    eocd = -1
    for i in range(len(buf) - 22, min_eocd - 1, -1):
        if i + 4 <= len(buf) and struct.unpack_from("<I", buf, i)[0] == 0x06054B50:
            eocd = i
            break
    if eocd < 0:
        return modes
    entry_count = struct.unpack_from("<H", buf, eocd + 10)[0]
    off = struct.unpack_from("<I", buf, eocd + 16)[0]
    for _ in range(entry_count):
        if off + 46 > len(buf):
            break
        if struct.unpack_from("<I", buf, off)[0] != 0x02014B50:
            break
        version_made_by = struct.unpack_from("<H", buf, off + 4)[0]
        name_len = struct.unpack_from("<H", buf, off + 28)[0]
        extra_len = struct.unpack_from("<H", buf, off + 30)[0]
        comment_len = struct.unpack_from("<H", buf, off + 32)[0]
        external_attr = struct.unpack_from("<I", buf, off + 38)[0]
        name = buf[off + 46: off + 46 + name_len].decode("utf-8", errors="replace")
        if (version_made_by >> 8) == 3:
            mode = (external_attr >> 16) & 0xFFFF
            if mode:
                modes[name] = mode
        off += 46 + name_len + extra_len + comment_len
    return modes


async def readAndUnzipFile(filePath: str) -> Dict[str, bytes]:
    """Reads a zip file from disk and unzips it."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        zip_data = await loop.run_in_executor(None, lambda: open(filePath, "rb").read())
        return await unzipFile(zip_data)
    except FileNotFoundError:
        raise
    except Exception as error:
        raise ValueError(f"Failed to read or unzip file: {error}")

"""Port of src/utils/readFileInRange.ts

Line-oriented file reader with fast path (< 10MB) and streaming path.
"""
from __future__ import annotations
import asyncio
import os
from typing import Any, Dict, Optional

FAST_PATH_MAX_SIZE = 10 * 1024 * 1024  # 10 MB

ReadFileRangeResult = Dict[str, Any]


def _format_file_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


class FileTooLargeError(Exception):
    def __init__(self, size_in_bytes: int, max_size_bytes: int):
        self.sizeInBytes = size_in_bytes
        self.maxSizeBytes = max_size_bytes
        super().__init__(
            f"File content ({_format_file_size(size_in_bytes)}) exceeds maximum allowed size "
            f"({_format_file_size(max_size_bytes)}). Use offset and limit parameters to read "
            f"specific portions of the file, or search for specific content instead of reading "
            f"the whole file."
        )
        self.name = "FileTooLargeError"


async def readFileInRange(
    file_path: str,
    offset: int = 0,
    max_lines: Optional[int] = None,
    max_bytes: Optional[int] = None,
    signal=None,
    options: Optional[Dict[str, Any]] = None,
) -> ReadFileRangeResult:
    """Read lines [offset, offset + max_lines) from a file."""
    truncate_on_byte_limit = (options or {}).get("truncateOnByteLimit", False)

    stat = os.stat(file_path)

    if os.path.isdir(file_path):
        raise IsADirectoryError(f"EISDIR: illegal operation on a directory, read '{file_path}'")

    if stat.st_size < FAST_PATH_MAX_SIZE:
        if not truncate_on_byte_limit and max_bytes is not None and stat.st_size > max_bytes:
            raise FileTooLargeError(stat.st_size, max_bytes)
        with open(file_path, "r", encoding="utf-8") as fh:
            raw = fh.read()
        return readFileInRangeFast(
            raw,
            stat.st_mtime_ns // 1_000_000,
            offset,
            max_lines,
            max_bytes if truncate_on_byte_limit else None,
        )

    return await _read_file_range_streaming(
        file_path,
        offset,
        max_lines,
        max_bytes,
        truncate_on_byte_limit,
    )


def readFileInRangeFast(
    raw: str,
    mtime_ms: float,
    offset: int,
    max_lines: Optional[int],
    truncate_at_bytes: Optional[int],
) -> ReadFileRangeResult:
    """Fast in-memory path for small files."""
    end_line = offset + max_lines if max_lines is not None else float("inf")

    # Strip BOM
    if raw and raw[0] == "\ufeff":
        raw = raw[1:]

    selected_lines = []
    selected_bytes = 0
    truncated_by_bytes = False
    line_index = 0
    pos = 0
    total_bytes = len(raw.encode("utf-8"))

    def try_push(line: str) -> bool:
        nonlocal selected_bytes, truncated_by_bytes
        if truncate_at_bytes is not None:
            sep = 1 if selected_lines else 0
            next_bytes = selected_bytes + sep + len(line.encode("utf-8"))
            if next_bytes > truncate_at_bytes:
                truncated_by_bytes = True
                return False
            selected_bytes = next_bytes
        selected_lines.append(line)
        return True

    while True:
        newline_pos = raw.find("\n", pos)
        if newline_pos == -1:
            break
        if line_index >= offset and line_index < end_line and not truncated_by_bytes:
            line = raw[pos:newline_pos]
            if line.endswith("\r"):
                line = line[:-1]
            try_push(line)
        line_index += 1
        pos = newline_pos + 1

    # Final fragment (no trailing newline)
    if line_index >= offset and line_index < end_line and not truncated_by_bytes:
        line = raw[pos:]
        if line.endswith("\r"):
            line = line[:-1]
        try_push(line)
    line_index += 1

    content = "\n".join(selected_lines)
    result = {
        "content": content,
        "lineCount": len(selected_lines),
        "totalLines": line_index,
        "totalBytes": total_bytes,
        "readBytes": len(content.encode("utf-8")),
        "mtimeMs": mtime_ms,
    }
    if truncated_by_bytes:
        result["truncatedByBytes"] = True
    return result


async def _read_file_range_streaming(
    file_path: str,
    offset: int,
    max_lines: Optional[int],
    max_bytes: Optional[int],
    truncate_on_byte_limit: bool,
) -> ReadFileRangeResult:
    """Streaming path for large files."""
    end_line = offset + max_lines if max_lines is not None else float("inf")
    selected_lines = []
    selected_bytes = 0
    truncated_by_bytes = False
    current_line_index = 0
    total_bytes_read = 0
    partial = ""
    is_first_chunk = True
    mtime_ms = os.stat(file_path).st_mtime_ns // 1_000_000

    def process_chunk(chunk: str) -> Optional[Exception]:
        nonlocal is_first_chunk, total_bytes_read, partial, current_line_index
        nonlocal selected_bytes, truncated_by_bytes, end_line

        if is_first_chunk:
            is_first_chunk = False
            if chunk and chunk[0] == "\ufeff":
                chunk = chunk[1:]

        total_bytes_read += len(chunk.encode("utf-8"))
        if not truncate_on_byte_limit and max_bytes is not None and total_bytes_read > max_bytes:
            return FileTooLargeError(total_bytes_read, max_bytes)

        data = partial + chunk
        partial = ""
        start = 0
        while True:
            nl = data.find("\n", start)
            if nl == -1:
                break
            if current_line_index >= offset and current_line_index < end_line:
                line = data[start:nl]
                if line.endswith("\r"):
                    line = line[:-1]
                if truncate_on_byte_limit and max_bytes is not None:
                    sep = 1 if selected_lines else 0
                    next_bytes = selected_bytes + sep + len(line.encode("utf-8"))
                    if next_bytes > max_bytes:
                        truncated_by_bytes = True
                        end_line = current_line_index
                    else:
                        selected_bytes = next_bytes
                        selected_lines.append(line)
                else:
                    selected_lines.append(line)
            current_line_index += 1
            start = nl + 1

        if start < len(data) and current_line_index >= offset and current_line_index < end_line:
            partial = data[start:]
        return None

    loop = asyncio.get_event_loop()
    chunk_size = 512 * 1024

    def read_sync():
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            while True:
                data = fh.read(chunk_size)
                if not data:
                    break
                err = process_chunk(data)
                if err:
                    raise err
        # finalize
        line = partial
        if line.endswith("\r"):
            line = line[:-1]
        nonlocal current_line_index
        if current_line_index >= offset and current_line_index < end_line:
            if truncate_on_byte_limit and max_bytes is not None:
                sep = 1 if selected_lines else 0
                next_bytes = selected_bytes + sep + len(line.encode("utf-8"))
                if next_bytes <= max_bytes:
                    selected_lines.append(line)
                else:
                    nonlocal truncated_by_bytes
                    truncated_by_bytes = True
            else:
                selected_lines.append(line)
        current_line_index += 1

    await loop.run_in_executor(None, read_sync)

    content = "\n".join(selected_lines)
    result = {
        "content": content,
        "lineCount": len(selected_lines),
        "totalLines": current_line_index,
        "totalBytes": total_bytes_read,
        "readBytes": len(content.encode("utf-8")),
        "mtimeMs": mtime_ms,
    }
    if truncated_by_bytes:
        result["truncatedByBytes"] = True
    return result

"""
FileEditTool core edit logic — mirrors src/tools/FileEditTool/editFile.ts
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
from .constants import FILE_UNEXPECTEDLY_MODIFIED_ERROR


class FileEditError(Exception):
    """Raised when a file edit operation fails."""
    def __init__(self, message: str, code: str = "EDIT_ERROR"):
        super().__init__(message)
        self.code = code


def countOccurrences(text: str, pattern: str) -> int:
    """Count the number of non-overlapping occurrences of pattern in text."""
    if not pattern:
        return 0
    count = 0
    start = 0
    while True:
        idx = text.find(pattern, start)
        if idx == -1:
            break
        count += 1
        start = idx + len(pattern)
    return count


def applyEdit(content: str, oldString: str, newString: str) -> str:
    """
    Apply a single string replacement to content.
    Raises FileEditError if oldString is not found or appears multiple times.
    """
    count = countOccurrences(content, oldString)
    if count == 0:
        raise FileEditError(
            f"String not found in file. The string may have been modified or does not "
            f"exist in the file.\n\nString:\n{oldString}",
            code="EDIT_NOT_FOUND",
        )
    if count > 1:
        raise FileEditError(
            f"String appears {count} times in file. Include more context lines to "
            f"uniquely identify the target location.\n\nString:\n{oldString}",
            code="EDIT_AMBIGUOUS",
        )
    return content.replace(oldString, newString, 1)


def editFile(
    filePath: str,
    oldString: str,
    newString: str,
    expectedHash: Optional[str] = None,
) -> str:
    """
    Edit a file by replacing oldString with newString.
    Returns the new file content.
    Raises FileEditError on any failure.
    """
    path = Path(filePath)
    if not path.exists():
        raise FileEditError(f"File not found: {filePath}", code="FILE_NOT_FOUND")

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        raise FileEditError(f"Cannot read file: {e}", code="READ_ERROR")

    # If expected hash provided, validate file hasn't changed
    if expectedHash:
        import hashlib
        actualHash = hashlib.sha256(content.encode()).hexdigest()[:16]
        if actualHash != expectedHash:
            raise FileEditError(FILE_UNEXPECTEDLY_MODIFIED_ERROR, code="MODIFIED")

    newContent = applyEdit(content, oldString, newString)

    try:
        path.write_text(newContent, encoding="utf-8")
    except OSError as e:
        raise FileEditError(f"Cannot write file: {e}", code="WRITE_ERROR")

    return newContent

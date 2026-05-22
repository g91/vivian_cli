"""FileEditTool utilities — mirrors src/tools/FileEditTool/utils.ts"""
from __future__ import annotations
import hashlib
import os
from typing import Optional, Tuple

def computeFileHash(filePath: str) -> Optional[str]:
    """Compute SHA-256 hash of a file's contents."""
    try:
        with open(filePath, "rb") as f:
            content = f.read()
        return hashlib.sha256(content).hexdigest()
    except (FileNotFoundError, PermissionError):
        return None

def verifyFileHash(filePath: str, expectedHash: str) -> bool:
    """Verify that a file's hash matches the expected hash."""
    actual = computeFileHash(filePath)
    return actual == expectedHash

def normalizeLineEndings(text: str) -> str:
    """Normalize line endings to LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")

def countOccurrences(text: str, pattern: str) -> int:
    """Count non-overlapping occurrences of pattern in text."""
    return text.count(pattern)

def validateFilePath(filePath: str, cwd: str = "") -> Tuple[bool, str]:
    """Validate that a file path is safe to edit."""
    if not cwd:
        cwd = os.getcwd()
    
    fullPath = os.path.expanduser(filePath)
    if not os.path.isabs(fullPath):
        fullPath = os.path.join(cwd, filePath)
    
    fullPath = os.path.normpath(fullPath)
    
    if not os.path.exists(os.path.dirname(fullPath)):
        return False, f"Parent directory does not exist: {os.path.dirname(fullPath)}"
    
    return True, fullPath

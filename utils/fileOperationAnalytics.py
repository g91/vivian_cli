"""
Port of src/utils/fileOperationAnalytics.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import hashlib

from ..services.analytics.index import logEvent


MAX_CONTENT_HASH_SIZE = 100 * 1024


def hashFilePath(filePath):
    """Creates a truncated SHA256 hash (16 chars) for file paths
Used for privacy-preserving analytics on file operations"""
    return hashlib.sha256(str(filePath).encode('utf-8')).hexdigest()[:16]


def hashFileContent(content):
    """Creates a full SHA256 hash (64 chars) for file contents
Used for deduplication and change detection analytics"""
    return hashlib.sha256(str(content).encode('utf-8')).hexdigest()


def logFileOperation(params=None):
    """Logs file operation analytics to Statsig"""
    params = params or {}
    metadata = {
        'operation': params.get('operation'),
        'tool': params.get('tool'),
        'filePathHash': hashFilePath(params.get('filePath', '')),
    }

    content = params.get('content')
    if content is not None and len(str(content)) <= MAX_CONTENT_HASH_SIZE:
        metadata['contentHash'] = hashFileContent(content)

    if params.get('type') is not None:
        metadata['type'] = params.get('type')

    logEvent('tengu_file_operation', metadata)


hash_file_path = hashFilePath
hash_file_content = hashFileContent
log_file_operation = logFileOperation


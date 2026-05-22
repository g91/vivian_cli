"""
passpasspass of src/utils/fileRead
"""
from __future__ import annotations

import os


LineEndingType = str


def detectEncodingForResolvedPath(resolvedPath):
    with open(resolvedPath, 'rb') as handle:
        head = handle.read(4096)

    if len(head) == 0:
        return 'utf-8'
    if len(head) >= 2 and head[0] == 0xFF and head[1] == 0xFE:
        return 'utf-16le'
    if len(head) >= 3 and head[0] == 0xEF and head[1] == 0xBB and head[2] == 0xBF:
        return 'utf-8-sig'
    return 'utf-8'


def detectLineEndingsForString(content):
    crlf_count = 0
    lf_count = 0
    for index, char in enumerate(content):
        if char == '\n':
            if index > 0 and content[index - 1] == '\r':
                crlf_count += 1
            else:
                lf_count += 1
    return 'CRLF' if crlf_count > lf_count else 'LF'


class ReadFileMetadata:
    def __init__(self, content: str, encoding: str, lineEndings: LineEndingType):
        self.content = content
        self.encoding = encoding
        self.lineEndings = lineEndings


def readFileSyncWithMetadata(filePath):
    """Like readFileSync but also returns the detected encoding and original line"""
    resolved_path = os.path.realpath(filePath)
    encoding = detectEncodingForResolvedPath(resolved_path)
    with open(resolved_path, 'r', encoding=encoding, newline='') as handle:
        raw = handle.read()
    line_endings = detectLineEndingsForString(raw[:4096])
    return ReadFileMetadata(
        content=raw.replace('\r\n', '\n'),
        encoding=encoding,
        lineEndings=line_endings,
    )


def readFileSync(filePath):
    return readFileSyncWithMetadata(filePath).content


detect_encoding_for_resolved_path = detectEncodingForResolvedPath
detect_line_endings_for_string = detectLineEndingsForString
read_file_sync_with_metadata = readFileSyncWithMetadata
read_file_sync = readFileSync


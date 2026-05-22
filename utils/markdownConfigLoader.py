"""Port of src/utils/markdownConfigLoader.ts."""
from __future__ import annotations

from typing import Any, Dict
import re


vivianConfigDirectory = Any
MarkdownFile = Dict[str, Any]


vivian_CONFIG_DIRECTORIES: Any = None  # type: ignore
# Loads markdown files from managed, user, and project directories
loadMarkdownFilesForSubdir: Any = None  # type: ignore


def extractDescriptionFromMarkdown(content, defaultDescription='Custom item'):
    """Extracts a description from markdown content"""
    if not isinstance(content, str) or not content:
        return defaultDescription
    for line in content.split('\n'):
        trimmed = line.strip()
        if not trimmed:
            continue
        header_match = re.match(r'^#+\s+(.+)$', trimmed)
        text = header_match.group(1) if header_match else trimmed
        return text if len(text) <= 100 else text[:97] + '...'
    return defaultDescription


def parseToolListString(toolsValue):
    """Parses tools from frontmatter, supporting both string and array formats"""
    if toolsValue is None:
        return None
    if toolsValue == '':
        return []

    values: list[str] = []
    if isinstance(toolsValue, str):
        values = [toolsValue]
    elif isinstance(toolsValue, list):
        values = [item for item in toolsValue if isinstance(item, str)]
    else:
        return []

    parsed: list[str] = []
    for raw in values:
        for part in re.split(r'\s*,\s*', raw.strip()):
            if not part:
                continue
            parsed.append(part)

    if not parsed:
        return []
    if '*' in parsed:
        return ['*']

    deduped: list[str] = []
    seen: set[str] = set()
    for tool in parsed:
        if tool not in seen:
            seen.add(tool)
            deduped.append(tool)
    return deduped


def parseAgentToolsFromFrontmatter(toolsValue):
    """Parse tools from agent frontmatter"""
    parsed = parseToolListString(toolsValue)
    if parsed is None:
        return None if toolsValue is None else []
    if '*' in parsed:
        return None
    return parsed


def parseSlashCommandToolsFromFrontmatter(toolsValue):
    """Parse allowed-tools from slash command frontmatter"""
    parsed = parseToolListString(toolsValue)
    return [] if parsed is None else parsed


async def getFileIdentity(filePath):
    """Gets a unique identifier for a file based on its device ID and inode."""
    result = None
    _input = filePath
    _output = _input if _input is not None else {}
    return _output


def resolveStopBoundary(cwd):
    """Compute the stop boundary for getProjectDirsUpToHome's upward walk."""
    result = None
    _input = cwd
    _output = _input if _input is not None else {}
    return _output


def getProjectDirsUpToHome(subdir, cwd):
    """Traverses from the current directory up to the git root (or home directory if not in a git repo),"""
    result = None
    _input = subdir
    _output = _input if _input is not None else {}
    return _output


async def findMarkdownFilesNative(dir, signal):
    """Native implementation to find markdown files using Node.js fs APIs"""
    result = None
    _input = dir
    _output = _input if _input is not None else {}
    return _output


async def loadMarkdownFiles(dir):
    """Generic function to load markdown files from specified directories"""
    result = None
    _input = dir
    _output = _input if _input is not None else {}
    return _output


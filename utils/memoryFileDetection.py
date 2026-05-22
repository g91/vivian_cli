"""
Port of src/utils/memoryFileDetection
"""
from __future__ import annotations

from typing import Literal
import re
from pathlib import Path

from ..memdir import (
    get_auto_mem_path,
    get_memory_base_dir,
    is_auto_memory_enabled,
    is_team_memory_enabled,
    get_team_memory_dir,
)
from ..tools.AgentTool.agentMemory import getAgentMemoryPath
from .envUtils import get_vivian_config_home_dir
from .windowsPaths import posixPathToWindowsPath


MemoryScope = Literal["personal", "team"]
IS_WINDOWS = Path("C:/").anchor.endswith(":\\") if hasattr(Path("C:/"), "anchor") else False


def toPosix(p):
    return str(p).replace("\\", "/")


def toComparable(p):
    posixForm = toPosix(p)
    return posixForm.lower() if IS_WINDOWS else posixForm


def detectSessionFileType(filePath):
    """Detects if a file path is a session-related file under ~/.vivian."""
    config_dir = get_vivian_config_home_dir()
    normalized = toComparable(filePath)
    config_dir_cmp = toComparable(config_dir)
    if not normalized.startswith(config_dir_cmp):
        return None
    if "/session-memory/" in normalized and normalized.endswith(".md"):
        return "session_memory"
    if "/projects/" in normalized and normalized.endswith(".jsonl"):
        return "session_transcript"
    return None


def detectSessionPatternType(pattern):
    """Checks if a glob/pattern string indicates session file access intent."""
    normalized = toPosix(pattern)
    if "session-memory" in normalized and (".md" in normalized or normalized.endswith("*")):
        return "session_memory"
    if ".jsonl" in normalized or ("projects" in normalized and "*.jsonl" in normalized):
        return "session_transcript"
    return None


def isAutoMemFile(filePath):
    """Check if a file path is within the memdir directory."""
    if not is_auto_memory_enabled():
        return False
    auto_mem_path = get_auto_mem_path() or str(Path(get_memory_base_dir()) / "memory")
    auto_mem_cmp = toComparable(str(auto_mem_path).rstrip("/\\") + "/")
    path_cmp = toComparable(filePath)
    return path_cmp.startswith(auto_mem_cmp)


def memoryScopeForPath(filePath):
    """Determine which memory store (if any) a path belongs to."""
    if is_team_memory_enabled():
        team_dir = get_team_memory_dir()
        if team_dir and toComparable(filePath).startswith(toComparable(str(team_dir).rstrip("/\\") + "/")):
            return "team"
    if isAutoMemFile(filePath):
        return "personal"
    return None


def isAgentMemFile(filePath):
    """Check if a file path is within an agent memory directory."""
    normalized = toComparable(filePath)
    return "/agent-memory/" in normalized or "/agent-memory-local/" in normalized or normalized.endswith("/memory.json") and "/.vivian/agents/" in normalized


def isAutoManagedMemoryFile(filePath):
    """Check if a file is a vivian-managed memory file (NOT user-managed instruction files)."""
    if isAutoMemFile(filePath):
        return True
    if memoryScopeForPath(filePath) == "team":
        return True
    if detectSessionFileType(filePath) is not None:
        return True
    if isAgentMemFile(filePath):
        return True
    return False


def isMemoryDirectory(dirPath):
    normalized_path = toComparable(Path(dirPath).as_posix() if dirPath else "")
    if not normalized_path:
        return False
    if is_auto_memory_enabled() and ("/agent-memory/" in normalized_path or "/agent-memory-local/" in normalized_path):
        return True
    if is_team_memory_enabled():
        team_dir = get_team_memory_dir()
        if team_dir and normalized_path.startswith(toComparable(str(team_dir))):
            return True
    auto_mem_path = get_auto_mem_path()
    if auto_mem_path:
        auto_mem_cmp = toComparable(str(auto_mem_path).rstrip("/\\"))
        if normalized_path == auto_mem_cmp or normalized_path.startswith(auto_mem_cmp + "/"):
            return True
    config_dir_cmp = toComparable(get_vivian_config_home_dir())
    memory_base_cmp = toComparable(get_memory_base_dir())
    under_config = normalized_path.startswith(config_dir_cmp)
    under_memory_base = normalized_path.startswith(memory_base_cmp)
    if not under_config and not under_memory_base:
        return False
    if normalized_path.endswith("/session-memory") or "/session-memory/" in normalized_path:
        return True
    if under_config and (
        normalized_path.endswith("/projects") or "/projects/" in normalized_path
    ):
        return True
    if is_auto_memory_enabled() and "/memory/" in normalized_path:
        return True
    return False


def isShellCommandTargetingMemory(command):
    """Check if a shell command string (Bash or PowerShell) targets memory files"""
    config_dir = get_vivian_config_home_dir()
    memory_base = get_memory_base_dir()
    auto_mem_dir = (get_auto_mem_path() or "").rstrip("/\\")
    command_cmp = toComparable(command)
    dirs = [config_dir, memory_base, auto_mem_dir]
    matches_any_dir = False
    for directory in filter(None, dirs):
        comparable = toComparable(directory)
        if comparable in command_cmp:
            matches_any_dir = True
            break
        if IS_WINDOWS and toComparable(posixPathToWindowsPath(directory)) in command_cmp:
            matches_any_dir = True
            break
    if not matches_any_dir:
        return False

    matches = re.findall(r"(?:[A-Za-z]:[/\\]|/)[^\s'\"]+", command)
    if not matches:
        return False
    for match in matches:
        clean_path = re.sub(r"[,;|&>]+$", "", match)
        native_path = posixPathToWindowsPath(clean_path) if IS_WINDOWS else clean_path
        if isAutoManagedMemoryFile(native_path) or isMemoryDirectory(native_path):
            return True
    return False


def isAutoManagedMemoryPattern(pattern):
    if detectSessionPatternType(pattern) is not None:
        return True
    normalized = toPosix(pattern)
    if is_auto_memory_enabled() and (
        "agent-memory/" in normalized or "agent-memory-local/" in normalized
    ):
        return True
    return False


detect_session_file_type = detectSessionFileType
detect_session_pattern_type = detectSessionPatternType
is_auto_mem_file = isAutoMemFile
memory_scope_for_path = memoryScopeForPath
is_agent_mem_file = isAgentMemFile
is_auto_managed_memory_file = isAutoManagedMemoryFile
is_memory_directory = isMemoryDirectory
is_shell_command_targeting_memory = isShellCommandTargetingMemory
is_auto_managed_memory_pattern = isAutoManagedMemoryPattern


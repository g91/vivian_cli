"""Pure-Python project-type and compiler detection.

Lives outside build_runner so the web GUI (which has no Qt dependency) can
share the same detection logic.
"""
from __future__ import annotations
import os
from enum import Enum
from typing import Optional


class ProjectKind(str, Enum):
    ESP_IDF = "esp-idf"
    MAKE = "make"
    C_SOURCE = "c-source"
    CPP_SOURCE = "cpp-source"
    UNKNOWN = "unknown"


def is_esp_idf_project(root: str) -> bool:
    """True if the workspace root looks like an ESP-IDF project."""
    try:
        entries = set(os.listdir(root))
    except OSError:
        return False
    if "sdkconfig" in entries or "sdkconfig.defaults" in entries:
        return True
    if "CMakeLists.txt" in entries:
        try:
            with open(os.path.join(root, "CMakeLists.txt"), "r", errors="replace") as f:
                content = f.read()
        except OSError:
            return False
        lc = content.lower()
        if "esp-idf" in lc or "idf_component" in content or "$env{idf_path}" in lc:
            return True
    return False


def compiler_for_file(path: str) -> Optional[dict]:
    """Return ``{"label": "g++", "argv": [...]}`` or None."""
    if not path:
        return None
    ext = os.path.splitext(path)[1].lower()
    stem = os.path.splitext(path)[0]
    recipes = {
        ".c":     ("gcc", ["gcc", path, "-o", stem, "-Wall"]),
        ".h":     ("gcc", ["gcc", path, "-o", stem, "-Wall"]),
        ".cpp":   ("g++", ["g++", path, "-o", stem, "-Wall", "-std=c++17"]),
        ".cc":    ("g++", ["g++", path, "-o", stem, "-Wall", "-std=c++17"]),
        ".cxx":   ("g++", ["g++", path, "-o", stem, "-Wall", "-std=c++17"]),
        ".hpp":   ("g++", ["g++", path, "-o", stem, "-Wall", "-std=c++17"]),
        ".cs":    ("dotnet build", ["dotnet", "build"]),
        ".rs":    ("cargo build", ["cargo", "build"]),
        ".go":    ("go build",   ["go", "build", "./..."]),
        ".java":  ("javac", ["javac", path]),
        ".ts":    ("tsc", ["tsc", path]),
        ".kt":    ("kotlinc", ["kotlinc", path, "-include-runtime", "-d",
                               stem + ".jar"]),
        ".swift": ("swiftc", ["swiftc", path, "-o", stem]),
    }
    hit = recipes.get(ext)
    if not hit:
        return None
    label, argv = hit
    return {"label": label, "argv": argv}


def detect_project(root: str, current_file: str = "") -> ProjectKind:
    if is_esp_idf_project(root):
        return ProjectKind.ESP_IDF
    try:
        entries = set(os.listdir(root))
    except OSError:
        entries = set()
    if "Makefile" in entries or "makefile" in entries or "GNUmakefile" in entries:
        return ProjectKind.MAKE
    if current_file:
        ext = os.path.splitext(current_file)[1].lower()
        if ext in (".c", ".h"):
            return ProjectKind.C_SOURCE
        if ext in (".cpp", ".cxx", ".cc", ".hpp"):
            return ProjectKind.CPP_SOURCE
    return ProjectKind.UNKNOWN

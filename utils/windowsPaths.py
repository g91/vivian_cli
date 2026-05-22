"""Windows path utilities — mirrors src/utils/windowsPaths.ts"""
from __future__ import annotations


def convert_wsl_path(wsl_path: str) -> str:
    if wsl_path.startswith("/mnt/"):
        parts = wsl_path[5:].split("/", 1)
        drive = parts[0].upper()
        rest = parts[1] if len(parts) > 1 else ""
        return f"{drive}:\\{rest.replace('/', '\\')}"
    return wsl_path


def convert_windows_path(win_path: str) -> str:
    if len(win_path) >= 2 and win_path[1] == ":":
        drive = win_path[0].lower()
        rest = win_path[2:].replace("\\", "/")
        return f"/mnt/{drive}{rest}"
    return win_path


windowsPathToPosixPath = convert_windows_path
posixPathToWindowsPath = convert_wsl_path

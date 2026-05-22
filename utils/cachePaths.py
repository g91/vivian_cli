"""Cache path helpers — mirrors src/utils/cachePaths.ts"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .hash import djb2_hash


def _get_cache_base() -> str:
    """Platform-appropriate cache base directory."""
    # Follow XDG on Linux, ~/Library/Caches on macOS, %LOCALAPPDATA% on Windows
    import sys
    if sys.platform == "darwin":
        return str(Path.home() / "Library" / "Caches" / "vivian-cli")
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        return str(Path(local) / "vivian-cli" / "Cache" if local else Path.home() / ".cache" / "vivian-cli")
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return str(Path(xdg) / "vivian-cli")
    return str(Path.home() / ".cache" / "vivian-cli")


_MAX_SANITIZED_LENGTH = 200


def _sanitize_path(name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9]", "-", name)
    if len(sanitized) <= _MAX_SANITIZED_LENGTH:
        return sanitized
    return f"{sanitized[:_MAX_SANITIZED_LENGTH]}-{abs(djb2_hash(name)):x}"


def _get_project_dir(cwd: str) -> str:
    return _sanitize_path(cwd)


class _CachePaths:
    """Lazily-evaluated cache path descriptors. Mirrors CACHE_PATHS from cachePaths.ts."""

    def base_logs(self, cwd: str | None = None) -> str:
        return str(Path(_get_cache_base()) / _get_project_dir(cwd or os.getcwd()))

    def errors(self, cwd: str | None = None) -> str:
        return str(Path(self.base_logs(cwd)) / "errors")

    def messages(self, cwd: str | None = None) -> str:
        return str(Path(self.base_logs(cwd)) / "messages")

    def mcp_logs(self, server_name: str, cwd: str | None = None) -> str:
        return str(Path(self.base_logs(cwd)) / f"mcp-logs-{_sanitize_path(server_name)}")


CACHE_PATHS = _CachePaths()

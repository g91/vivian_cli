"""Binary availability check — mirrors src/utils/binaryCheck.ts"""
from __future__ import annotations

from .which import which_sync

_binary_cache: dict[str, bool] = {}


async def is_binary_installed(command: str) -> bool:
    """Return True if the given command is available on PATH."""
    if not command or not command.strip():
        return False
    cmd = command.strip()
    if cmd in _binary_cache:
        return _binary_cache[cmd]
    exists = which_sync(cmd) is not None
    _binary_cache[cmd] = exists
    return exists


def is_binary_installed_sync(command: str) -> bool:
    """Synchronous version of is_binary_installed."""
    if not command or not command.strip():
        return False
    cmd = command.strip()
    if cmd in _binary_cache:
        return _binary_cache[cmd]
    exists = which_sync(cmd) is not None
    _binary_cache[cmd] = exists
    return exists


def clear_binary_cache() -> None:
    """Clear the binary check cache."""
    _binary_cache.clear()


async def isBinaryInstalled(command: str) -> bool:
    return await is_binary_installed(command)


def isBinaryInstalledSync(command: str) -> bool:
    return is_binary_installed_sync(command)


def clearBinaryCache() -> None:
    clear_binary_cache()

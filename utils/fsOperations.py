"""File system operations wrapper — mirrors src/utils/fsOperations.ts"""
from __future__ import annotations

import os
import shutil
from typing import Any


def exists_sync(path: str) -> bool:
    """Return True if the path exists."""
    return os.path.exists(path)


def stat_sync(path: str) -> os.stat_result:
    """Return stat result for path."""
    return os.stat(path)


async def stat_async(path: str) -> os.stat_result:
    """Async stat."""
    return os.stat(path)


async def readdir(path: str) -> list:
    """List directory entries."""
    return list(os.scandir(path))


async def unlink(path: str) -> None:
    """Delete a file."""
    os.unlink(path)


async def rmdir(path: str) -> None:
    """Remove an empty directory."""
    os.rmdir(path)


async def rm(path: str, *, recursive: bool = False, force: bool = False) -> None:
    """Remove a file or directory."""
    try:
        if recursive and os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.unlink(path)
    except FileNotFoundError:
        if not force:
            raise


async def mkdir(path: str, *, mode: int = 0o755) -> None:
    """Create directory recursively."""
    os.makedirs(path, mode=mode, exist_ok=True)


async def read_file(path: str, encoding: str = "utf-8") -> str:
    """Read file as string."""
    with open(path, "r", encoding=encoding) as f:
        return f.read()


async def write_file(path: str, data: str, *, encoding: str = "utf-8") -> None:
    """Write string to file."""
    with open(path, "w", encoding=encoding) as f:
        f.write(data)


async def rename(old_path: str, new_path: str) -> None:
    """Rename/move a file."""
    os.rename(old_path, new_path)


class _FsImplementation:
    def cwd(self) -> str:
        return os.getcwd()

    def existsSync(self, path: str) -> bool:
        return exists_sync(path)

    async def stat(self, path: str):
        return await stat_async(path)

    def statSync(self, path: str):
        return stat_sync(path)

    async def readdir(self, path: str):
        return await readdir(path)

    async def unlink(self, path: str) -> None:
        await unlink(path)

    async def rmdir(self, path: str) -> None:
        await rmdir(path)

    async def rm(self, path: str, *, recursive: bool = False, force: bool = False) -> None:
        await rm(path, recursive=recursive, force=force)

    async def mkdir(self, path: str, *, mode: int = 0o755) -> None:
        await mkdir(path, mode=mode)

    async def readFile(self, path: str, encoding: str = "utf-8") -> str:
        return await read_file(path, encoding=encoding)

    async def writeFile(self, path: str, data: str, *, encoding: str = "utf-8") -> None:
        await write_file(path, data, encoding=encoding)

    async def rename(self, old_path: str, new_path: str) -> None:
        await rename(old_path, new_path)


_FS_IMPLEMENTATION = _FsImplementation()


def get_fs_implementation() -> _FsImplementation:
    return _FS_IMPLEMENTATION


def getFsImplementation() -> _FsImplementation:
    return get_fs_implementation()


def isDuplicatePath(_fs: Any, full_path: str, loaded_paths: set[str]) -> bool:
    normalized = os.path.realpath(full_path)
    if normalized in loaded_paths:
        return True
    loaded_paths.add(normalized)
    return False

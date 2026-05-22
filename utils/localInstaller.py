"""
Port of src/utils/localInstaller.ts
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal, Optional

from .config import save_global_config
from .envUtils import get_vivian_config_home_dir
from .errors import get_errno_code
from .execFileNoThrow import exec_file_no_throw
from .log import logError
from .slowOperations import jsonStringify


ReleaseChannel = Literal["latest", "stable"]
_DEFAULT_PACKAGE_URL = os.environ.get("vivian_CODE_PACKAGE_URL") or "@anthropic-ai/vivian-code"


def getLocalInstallDir():
    return os.path.join(get_vivian_config_home_dir(), "local")


def getLocalvivianPath():
    return os.path.join(getLocalInstallDir(), "vivian")


def isRunningFromLocalInstallation():
    """Check if we're running from our managed local installation"""
    exec_path = sys.argv[1] if len(sys.argv) > 1 else (sys.argv[0] if sys.argv else "")
    return "/.vivian/local/node_modules/" in (exec_path or "")


async def writeIfMissing(path, content, mode=None):
    """Write `content` to `path` only if the file does not already exist.
Uses O_EXCL ('wx') for atomic create-if-missing."""
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY

    def _write() -> bool:
        try:
            descriptor = os.open(path, flags, mode if mode is not None else 0o666)
        except OSError as error:
            if get_errno_code(error) == "EEXIST":
                return False
            raise
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(content)
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            raise
        return True

    return _write()


async def ensureLocalPackageEnvironment():
    """Ensure the local package environment is set up
Creates the directory, package.json, and wrapper script"""
    try:
        local_install_dir = getLocalInstallDir()
        os.makedirs(local_install_dir, exist_ok=True)

        await writeIfMissing(
            os.path.join(local_install_dir, "package.json"),
            jsonStringify({"name": "vivian-local", "version": "0.0.1", "private": True}, indent=2),
        )

        wrapper_path = getLocalvivianPath()
        created = await writeIfMissing(
            wrapper_path,
            f'#!/bin/sh\nexec "{local_install_dir}/node_modules/.bin/vivian" "$@"',
            0o755,
        )
        if created:
            os.chmod(wrapper_path, 0o755)
        return True
    except Exception as error:
        logError(error)
        return False


async def installOrUpdatevivianPackage(channel: ReleaseChannel, specificVersion=None):
    """Install or update vivian CLI package in the local directory
@param channel - Release channel to use (latest or stable)
@param specificVersion - Optional specific version to install (overrides channel)"""
    try:
        if not await ensureLocalPackageEnvironment():
            return "install_failed"

        version_spec = specificVersion or ("stable" if channel == "stable" else "latest")
        result = await exec_file_no_throw(
            "npm",
            ["install", f"{_DEFAULT_PACKAGE_URL}@{version_spec}"],
            cwd=getLocalInstallDir(),
            timeout=600,
        )

        if result.get("code") != 0:
            logError(Exception(f"Failed to install vivian CLI package: {result.get('stderr', '')}"))
            return "in_progress" if result.get("code") == 190 else "install_failed"

        save_global_config(lambda current: {**current, "installMethod": "local"})
        return "success"
    except Exception as error:
        logError(error)
        return "install_failed"


async def localInstallationExists():
    """Check if local installation exists.
Pure existence probe — callers use this to choose update path / UI hints."""
    return Path(getLocalInstallDir(), "node_modules", ".bin", "vivian").exists()


def getShellType():
    """Get shell type to determine appropriate path setup"""
    shell_path = os.environ.get("SHELL", "")
    if "zsh" in shell_path:
        return "zsh"
    if "bash" in shell_path:
        return "bash"
    if "fish" in shell_path:
        return "fish"
    return "unknown"


get_local_install_dir = getLocalInstallDir
get_local_vivian_path = getLocalvivianPath
is_running_from_local_installation = isRunningFromLocalInstallation
write_if_missing = writeIfMissing
ensure_local_package_environment = ensureLocalPackageEnvironment
install_or_update_vivian_package = installOrUpdatevivianPackage
local_installation_exists = localInstallationExists
get_shell_type = getShellType


"""Port of src/utils/envDynamic.ts."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Optional
import os
import asyncio
import platform

from .env import JETBRAINS_IDES, env
from .envUtils import is_env_truthy
from .execFileNoThrow import exec_file_no_throw
from .genericProcessUtils import getAncestorCommandsAsync


_docker_cache: Optional[bool] = None
_musl_runtime_cache: Optional[bool] = None
jetBrainsIDECache: Optional[str] = None
_jetbrains_cache_initialized = False


def getIsBubblewrapSandbox():
    return (
        env.platform == 'linux' and
        is_env_truthy(os.environ.get("vivian_CODE_BUBBLEWRAP", ""))
    )


async def getIsDocker() -> bool:
    global _docker_cache
    if _docker_cache is not None:
        return _docker_cache
    if env.platform != 'linux':
        _docker_cache = False
        return False
    result = await exec_file_no_throw('test', ['-f', '/.dockerenv'])
    _docker_cache = result.get('code') == 0
    return _docker_cache


def isMuslEnvironment():
    """Checks if the system is using MUSL libc instead of glibc.
In native linux builds, this is statically known at compile time via IS_LIBC_MUSL/IS_LIBC_GLIBC flags.
In node (unbundled), both flags are false and we fall back to a runtime async stat check
whose result is cached at module load. If the cache isn't populated yet, returns false."""
    global _musl_runtime_cache
    if env.platform != 'linux':
        return False
    if _musl_runtime_cache is None:
        arch = 'x86_64' if platform.machine().lower() in ('x86_64', 'amd64') else 'aarch64'
        _musl_runtime_cache = os.path.exists(f'/lib/libc.musl-{arch}.so.1')
    return _musl_runtime_cache


async def detectJetBrainsIDEFromParentProcessAsync():
    global jetBrainsIDECache, _jetbrains_cache_initialized
    if _jetbrains_cache_initialized:
        return jetBrainsIDECache

    if env.platform == 'darwin':
        _jetbrains_cache_initialized = True
        jetBrainsIDECache = None
        return None

    try:
        commands = await getAncestorCommandsAsync(os.getpid(), 10)
        for command in commands:
            lower_command = command.lower()
            for ide in JETBRAINS_IDES:
                if ide in lower_command:
                    jetBrainsIDECache = ide
                    _jetbrains_cache_initialized = True
                    return ide
    except Exception:
        pass

    _jetbrains_cache_initialized = True
    jetBrainsIDECache = None
    return None


async def getTerminalWithJetBrainsDetectionAsync():
    # Check for JetBrains terminal on Linux/Windows
    if os.environ.get("TERMINAL_EMULATOR", "") == 'JetBrains-JediTerm':
        # For macOS, bundle ID detection above already handles JetBrains IDEs
        if env.platform != 'darwin':
            specificIDE = await detectJetBrainsIDEFromParentProcessAsync()
            return specificIDE or 'pycharm'
    return env.terminal


def getTerminalWithJetBrainsDetection():
    # Check for JetBrains terminal on Linux/Windows
    if os.environ.get("TERMINAL_EMULATOR", "") == 'JetBrains-JediTerm':
        # For macOS, bundle ID detection above already handles JetBrains IDEs
        if env.platform != 'darwin':
            # Return cached value if available, otherwise fall back to generic detection
            # The async version should be called early in app initialization to populate cache
            if _jetbrains_cache_initialized:
                return jetBrainsIDECache or 'pycharm'
            # Fall back to generic 'pycharm' if cache not populated yet
            return 'pycharm'
    return env.terminal


async def initJetBrainsDetection():
    """Initialize JetBrains IDE detection asynchronously.
Call this early in app initialization to populate the cache.
After this resolves, getTerminalWithJetBrainsDetection() will return accurate results."""
    if os.environ.get("TERMINAL_EMULATOR", "") == 'JetBrains-JediTerm':
        await detectJetBrainsIDEFromParentProcessAsync()


_env_dynamic_values = dict(vars(env))
_env_dynamic_values.update(
    {
        'terminal': getTerminalWithJetBrainsDetection(),
        'getIsDocker': getIsDocker,
        'getIsBubblewrapSandbox': getIsBubblewrapSandbox,
        'isMuslEnvironment': isMuslEnvironment,
        'getTerminalWithJetBrainsDetectionAsync': getTerminalWithJetBrainsDetectionAsync,
        'initJetBrainsDetection': initJetBrainsDetection,
    }
)
envDynamic = SimpleNamespace(**_env_dynamic_values)


get_is_docker = getIsDocker
get_is_bubblewrap_sandbox = getIsBubblewrapSandbox
is_musl_environment = isMuslEnvironment
detect_jetbrains_ide_from_parent_process_async = detectJetBrainsIDEFromParentProcessAsync
get_terminal_with_jetbrains_detection_async = getTerminalWithJetBrainsDetectionAsync
get_terminal_with_jetbrains_detection = getTerminalWithJetBrainsDetection
init_jetbrains_detection = initJetBrainsDetection


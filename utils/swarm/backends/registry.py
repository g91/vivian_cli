"""Port of src/utils/swarm/backends/registry.ts."""
from __future__ import annotations

from importlib import import_module

from ....bootstrap.state import getIsNonInteractiveSession
from ...debug import logForDebugging
from ...platform import get_platform
from .InProcessBackend import createInProcessBackend
from .detection import isInITerm2, isInsideTmux, isInsideTmuxSync, isIt2CliAvailable, isTmuxAvailable, resetDetectionCache
from .it2Setup import getPreferTmuxOverIterm2
from .teammateModeSnapshot import getTeammateModeFromSnapshot


_cached_backend = None
_cached_detection_result = None
_backends_registered = False
_cached_in_process_backend = None
_cached_pane_backend_executor = None
_in_process_fallback_active = False
_tmux_backend_class = None
_iterm_backend_class = None
_tmux_backend_error: str | None = None
_iterm_backend_error: str | None = None


async def ensureBackendsRegistered() -> None:
    global _backends_registered, _tmux_backend_class, _iterm_backend_class
    global _tmux_backend_error, _iterm_backend_error
    if _backends_registered:
        return

    try:
        module = import_module("vivian_cli.utils.swarm.backends.TmuxBackend")
        _tmux_backend_class = getattr(module, "TmuxBackend", None)
    except Exception as error:
        _tmux_backend_error = str(error)
        logForDebugging(f"[BackendRegistry] Failed to import TmuxBackend: {error}")

    try:
        module = import_module("vivian_cli.utils.swarm.backends.ITermBackend")
        _iterm_backend_class = getattr(module, "ITermBackend", None)
    except Exception as error:
        _iterm_backend_error = str(error)
        logForDebugging(f"[BackendRegistry] Failed to import ITermBackend: {error}")

    _backends_registered = True


def registerTmuxBackend(backendClass=None):
    global _tmux_backend_class, _tmux_backend_error
    _tmux_backend_class = backendClass
    _tmux_backend_error = None


def registerITermBackend(backendClass=None):
    global _iterm_backend_class, _iterm_backend_error
    _iterm_backend_class = backendClass
    _iterm_backend_error = None
    logForDebugging(
        f"[registry] registerITermBackend called, class={getattr(backendClass, '__name__', 'undefined')}"
    )


def createTmuxBackend():
    if _tmux_backend_class is None:
        detail = f" ({_tmux_backend_error})" if _tmux_backend_error else ""
        raise RuntimeError(
            "TmuxBackend not registered. Import TmuxBackend.py before using the registry." + detail
        )
    return _tmux_backend_class()


def createITermBackend():
    if _iterm_backend_class is None:
        detail = f" ({_iterm_backend_error})" if _iterm_backend_error else ""
        raise RuntimeError(
            "ITermBackend not registered. Import ITermBackend.py before using the registry." + detail
        )
    return _iterm_backend_class()


async def detectAndGetBackend():
    global _cached_backend, _cached_detection_result

    await ensureBackendsRegistered()

    if _cached_detection_result is not None:
        logForDebugging(
            f"[BackendRegistry] Using cached backend: {_cached_detection_result['backend'].type}"
        )
        return _cached_detection_result

    logForDebugging("[BackendRegistry] Starting backend detection...")
    inside_tmux = await isInsideTmux()
    in_iterm2 = isInITerm2()
    logForDebugging(
        f"[BackendRegistry] Environment: insideTmux={inside_tmux}, inITerm2={in_iterm2}"
    )

    if inside_tmux:
        backend = createTmuxBackend()
        _cached_backend = backend
        _cached_detection_result = {
            "backend": backend,
            "isNative": True,
            "needsIt2Setup": False,
        }
        return _cached_detection_result

    if in_iterm2:
        prefer_tmux = getPreferTmuxOverIterm2()
        if not prefer_tmux:
            it2_available = await isIt2CliAvailable()
            logForDebugging(
                f"[BackendRegistry] iTerm2 detected, it2 CLI available: {it2_available}"
            )
            if it2_available:
                backend = createITermBackend()
                _cached_backend = backend
                _cached_detection_result = {
                    "backend": backend,
                    "isNative": True,
                    "needsIt2Setup": False,
                }
                return _cached_detection_result
        else:
            logForDebugging(
                "[BackendRegistry] User prefers tmux over iTerm2, skipping iTerm2 detection"
            )

        tmux_available = await isTmuxAvailable()
        logForDebugging(
            f"[BackendRegistry] it2 not available, tmux available: {tmux_available}"
        )
        if tmux_available:
            backend = createTmuxBackend()
            _cached_backend = backend
            _cached_detection_result = {
                "backend": backend,
                "isNative": False,
                "needsIt2Setup": not prefer_tmux,
            }
            return _cached_detection_result

        raise RuntimeError(
            "iTerm2 detected but it2 CLI not installed. Install it2 with: pip install it2"
        )

    tmux_available = await isTmuxAvailable()
    logForDebugging(
        f"[BackendRegistry] Not in tmux or iTerm2, tmux available: {tmux_available}"
    )
    if tmux_available:
        backend = createTmuxBackend()
        _cached_backend = backend
        _cached_detection_result = {
            "backend": backend,
            "isNative": False,
            "needsIt2Setup": False,
        }
        return _cached_detection_result

    raise RuntimeError(getTmuxInstallInstructions())


def getTmuxInstallInstructions() -> str:
    current_platform = get_platform()
    if current_platform == "macos":
        return "To use agent swarms, install tmux:\n  brew install tmux\nThen start a tmux session with: tmux new-session -s vivian"
    if current_platform in {"linux", "wsl"}:
        return "To use agent swarms, install tmux:\n  sudo apt install tmux    # Ubuntu/Debian\n  sudo dnf install tmux    # Fedora/RHEL\nThen start a tmux session with: tmux new-session -s vivian"
    if current_platform == "windows":
        return "To use agent swarms, you need tmux which requires WSL (Windows Subsystem for Linux).\nInstall WSL first, then inside WSL run:\n  sudo apt install tmux\nThen start a tmux session with: tmux new-session -s vivian"
    return "To use agent swarms, install tmux using your system's package manager.\nThen start a tmux session with: tmux new-session -s vivian"


def getBackendByType(type):
    if type == "tmux":
        return createTmuxBackend()
    if type == "iterm2":
        return createITermBackend()
    raise ValueError(f"Unknown backend type: {type}")


def getCachedBackend():
    return _cached_backend


def getCachedDetectionResult():
    return _cached_detection_result


def markInProcessFallback():
    global _in_process_fallback_active
    logForDebugging("[BackendRegistry] Marking in-process fallback as active")
    _in_process_fallback_active = True


def getTeammateMode():
    return getTeammateModeFromSnapshot()


def isInProcessEnabled():
    if getIsNonInteractiveSession():
        logForDebugging(
            "[BackendRegistry] isInProcessEnabled: true (non-interactive session)"
        )
        return True

    mode = getTeammateMode()
    if mode == "in-process":
        enabled = True
    elif mode == "tmux":
        enabled = False
    else:
        if _in_process_fallback_active:
            logForDebugging(
                "[BackendRegistry] isInProcessEnabled: true (fallback after pane backend unavailable)"
            )
            return True
        inside_tmux = isInsideTmuxSync()
        in_iterm2 = isInITerm2()
        enabled = not inside_tmux and not in_iterm2

    logForDebugging(
        f"[BackendRegistry] isInProcessEnabled: {enabled} (mode={mode}, insideTmux={isInsideTmuxSync()}, inITerm2={isInITerm2()})"
    )
    return enabled


def getResolvedTeammateMode():
    return "in-process" if isInProcessEnabled() else "tmux"


def getInProcessBackend():
    global _cached_in_process_backend
    if _cached_in_process_backend is None:
        _cached_in_process_backend = createInProcessBackend()
    return _cached_in_process_backend


async def getTeammateExecutor(preferInProcess=False):
    if preferInProcess and isInProcessEnabled():
        logForDebugging("[BackendRegistry] Using in-process executor")
        return getInProcessBackend()
    logForDebugging("[BackendRegistry] Using pane backend executor")
    return await getPaneBackendExecutor()


async def getPaneBackendExecutor():
    global _cached_pane_backend_executor
    if _cached_pane_backend_executor is None:
        from .PaneBackendExecutor import createPaneBackendExecutor

        detection = await detectAndGetBackend()
        _cached_pane_backend_executor = createPaneBackendExecutor(detection["backend"])
        logForDebugging(
            f"[BackendRegistry] Created PaneBackendExecutor wrapping {detection['backend'].type}"
        )
    return _cached_pane_backend_executor


def resetBackendDetection():
    global _cached_backend, _cached_detection_result, _backends_registered
    global _cached_in_process_backend, _cached_pane_backend_executor
    global _in_process_fallback_active, _tmux_backend_class, _iterm_backend_class
    global _tmux_backend_error, _iterm_backend_error

    _cached_backend = None
    _cached_detection_result = None
    _backends_registered = False
    _cached_in_process_backend = None
    _cached_pane_backend_executor = None
    _in_process_fallback_active = False
    _tmux_backend_class = None
    _iterm_backend_class = None
    _tmux_backend_error = None
    _iterm_backend_error = None
    resetDetectionCache()


ensure_backends_registered = ensureBackendsRegistered
register_tmux_backend = registerTmuxBackend
register_iterm_backend = registerITermBackend
create_tmux_backend = createTmuxBackend
create_iterm_backend = createITermBackend
detect_and_get_backend = detectAndGetBackend
get_tmux_install_instructions = getTmuxInstallInstructions
get_backend_by_type = getBackendByType
get_cached_backend = getCachedBackend
get_cached_detection_result = getCachedDetectionResult
mark_in_process_fallback = markInProcessFallback
get_teammate_mode = getTeammateMode
is_in_process_enabled = isInProcessEnabled
get_resolved_teammate_mode = getResolvedTeammateMode
get_in_process_backend = getInProcessBackend
get_teammate_executor = getTeammateExecutor
get_pane_backend_executor = getPaneBackendExecutor
reset_backend_detection = resetBackendDetection
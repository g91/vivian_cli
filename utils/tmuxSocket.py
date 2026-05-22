"""Port of src/utils/tmuxSocket.ts."""
from __future__ import annotations

from typing import Any, Dict, Optional
import os
import asyncio
import posixpath

from .cleanupRegistry import register_cleanup
from .debug import logForDebugging
from .errors import to_error
from .execFileNoThrow import exec_file_no_throw
from .platform import get_platform


TMUX_COMMAND = "tmux"
vivian_SOCKET_PREFIX = "vivian"

socketName: Optional[str] = None
socketPath: Optional[str] = None
serverPid: Optional[int] = None
isInitializing = False
initPromise: Optional[asyncio.Task[None]] = None
tmuxAvailabilityChecked = False
tmuxAvailable = False
tmuxToolUsed = False


async def execTmux(args, opts=None):
    """Executes a tmux command, routing through WSL on Windows.
On Windows, tmux only exists inside WSL — WSL interop lets the tmux session
launch .exe files as native Win32 processes while stdin/stdout flow through
the WSL pty."""
    opts = opts or {}
    if get_platform() == "windows":
        result = await exec_file_no_throw(
            "wsl",
            ["-e", TMUX_COMMAND, *args],
            env={**os.environ, "WSL_UTF8": "1", **(opts.get("env") or {})},
            cwd=opts.get("cwd"),
        )
    else:
        result = await exec_file_no_throw(
            TMUX_COMMAND,
            list(args),
            env=opts.get("env"),
            cwd=opts.get("cwd"),
        )
    return {
        "stdout": result.get("stdout", "") or "",
        "stderr": result.get("stderr", "") or "",
        "code": result.get("code", 0) or 0,
    }


def getvivianSocketName():
    """Gets the socket name for vivian's isolated tmux session.
Format: vivian-<PID>"""
    global socketName
    if not socketName:
        socketName = f"{vivian_SOCKET_PREFIX}-{os.getpid()}"
    return socketName


def getvivianSocketPath():
    """Gets the socket path if the socket has been initialized.
Returns null if not yet initialized."""
    return socketPath


def setvivianSocketInfo(path, pid):
    """Sets socket info after initialization.
Called after the tmux session is created."""
    global socketPath, serverPid
    socketPath = path
    serverPid = pid


def isSocketInitialized():
    """Returns whether the socket has been initialized."""
    return socketPath is not None and serverPid is not None


def getvivianTmuxEnv():
    """Gets the TMUX environment variable value for vivian's isolated socket.

CRITICAL: This value is used by Shell.ts to override the TMUX env var
in ALL child processes. This ensures that any `tmux` command run via
the Bash tool will operate on vivian's socket, NOT the user's session.

Format: "socket_path,server_pid,pane_index" (matches tmux's TMUX env var)
Example: "/tmp/tmux-501/vivian-12345,54321,0"

Returns null if socket is not yet initialized.
When null, Shell.ts does not override TMUX, preserving user's environment."""
    if not socketPath or serverPid is None:
        return None
    return f"{socketPath},{serverPid},0"


async def checkTmuxAvailable():
    """Checks if tmux is available on this system.
This is checked once and cached for the lifetime of the process.

When tmux is not available:
- TungstenTool (Tmux) will not work
- TeammateTool will not work (it uses tmux for pane management)
- Bash commands will run without tmux isolation"""
    global tmuxAvailabilityChecked, tmuxAvailable
    if not tmuxAvailabilityChecked:
        if get_platform() == "windows":
            result = await exec_file_no_throw(
                "wsl",
                ["-e", TMUX_COMMAND, "-V"],
                env={**os.environ, "WSL_UTF8": "1"},
            )
        else:
            result = await exec_file_no_throw("which", [TMUX_COMMAND])
        tmuxAvailable = result.get("code", -1) == 0
        if not tmuxAvailable:
            logForDebugging(
                "[Socket] tmux is not installed. The Tmux tool and Teammate tool will not be available."
            )
        tmuxAvailabilityChecked = True
    return tmuxAvailable


def isTmuxAvailable():
    """Returns the cached tmux availability status.
Returns false if availability hasn't been checked yet.
Use checkTmuxAvailable() to perform the check."""
    return tmuxAvailabilityChecked and tmuxAvailable


def markTmuxToolUsed():
    """Marks that the Tmux tool has been used at least once.
Called by TungstenTool before initialization.
After this is called, Shell.ts will initialize the socket for subsequent Bash commands."""
    global tmuxToolUsed
    tmuxToolUsed = True


def hasTmuxToolBeenUsed():
    """Returns whether the Tmux tool has been used at least once.
Used by Shell.ts to decide whether to initialize the socket."""
    return tmuxToolUsed


async def ensureSocketInitialized():
    """Ensures the socket is initialized with a tmux session.
Called by Shell.ts when the Tmux tool has been used or the command includes "tmux".
Safe to call multiple times; will only initialize once.

If tmux is not installed, this function returns gracefully without
initializing the socket. getvivianTmuxEnv() will return null, and
Bash commands will run without tmux isolation."""
    global isInitializing, initPromise
    if isSocketInitialized():
        return

    if not await checkTmuxAvailable():
        return

    if isInitializing and initPromise is not None:
        try:
            await initPromise
        except Exception:
            pass
        return

    isInitializing = True
    initPromise = asyncio.create_task(doInitialize())
    try:
        await initPromise
    except Exception as error:
        err = to_error(error)
        try:
            from .debug import logError

            logError("Failed to initialize tmux socket", err)
        except Exception:
            pass
        logForDebugging(
            f"[Socket] Failed to initialize tmux socket: {err}. Tmux isolation will be disabled."
        )
    finally:
        isInitializing = False


async def killTmuxServer():
    """Kills the tmux server for vivian's isolated socket.
Called during graceful shutdown to clean up resources."""
    socket_name = getvivianSocketName()
    logForDebugging(f"[Socket] Killing tmux server for socket: {socket_name}")
    result = await execTmux(["-L", socket_name, "kill-server"])
    if result["code"] == 0:
        logForDebugging("[Socket] Successfully killed tmux server")
    else:
        logForDebugging(
            f"[Socket] Failed to kill tmux server (exit {result['code']}): {result['stderr']}"
        )


async def doInitialize():
    socket_name = getvivianSocketName()
    args = [
        "-L",
        socket_name,
        "new-session",
        "-d",
        "-s",
        "base",
        "-e",
        "vivian_CODE_SKIP_PROMPT_HISTORY=true",
    ]
    if get_platform() == "windows":
        args.extend(["-e", "WSL_INTEROP=/run/WSL/1_interop"])

    result = await execTmux(args)
    if result["code"] != 0:
        check_result = await execTmux(["-L", socket_name, "has-session", "-t", "base"])
        if check_result["code"] != 0:
            raise RuntimeError(
                f"Failed to create tmux session on socket {socket_name}: {result['stderr']}"
            )

    register_cleanup(killTmuxServer)

    await execTmux(
        [
            "-L",
            socket_name,
            "set-environment",
            "-g",
            "vivian_CODE_SKIP_PROMPT_HISTORY",
            "true",
        ]
    )

    if get_platform() == "windows":
        await execTmux(
            [
                "-L",
                socket_name,
                "set-environment",
                "-g",
                "WSL_INTEROP",
                "/run/WSL/1_interop",
            ]
        )

    info_result = await execTmux(["-L", socket_name, "display-message", "-p", "#{socket_path},#{pid}"])
    if info_result["code"] == 0:
        parts = info_result["stdout"].strip().split(",")
        if len(parts) == 2 and parts[0] and parts[1]:
            try:
                pid = int(parts[1], 10)
            except ValueError:
                pid = -1
            if pid >= 0:
                setvivianSocketInfo(parts[0], pid)
                return
        logForDebugging(
            f"[Socket] Failed to parse socket info from tmux output: \"{info_result['stdout'].strip()}\". Using fallback path."
        )
    else:
        logForDebugging(
            f"[Socket] Failed to get socket info via display-message (exit {info_result['code']}): {info_result['stderr']}. Using fallback path."
        )

    uid = os.getuid() if hasattr(os, "getuid") else 0
    base_tmp_dir = os.environ.get("TMPDIR") or "/tmp"
    fallback_path = posixpath.join(base_tmp_dir, f"tmux-{uid}", socket_name)

    pid_result = await execTmux(["-L", socket_name, "display-message", "-p", "#{pid}"])
    if pid_result["code"] == 0:
        try:
            pid = int(pid_result["stdout"].strip(), 10)
        except ValueError:
            pid = -1
        if pid >= 0:
            logForDebugging(
                f"[Socket] Using fallback socket path: {fallback_path} (server PID: {pid})"
            )
            setvivianSocketInfo(fallback_path, pid)
            return
        logForDebugging(
            f"[Socket] Failed to parse server PID from tmux output: \"{pid_result['stdout'].strip()}\""
        )
    else:
        logForDebugging(
            f"[Socket] Failed to get server PID (exit {pid_result['code']}): {pid_result['stderr']}"
        )

    raise RuntimeError(
        f"Failed to get socket info for {socket_name}: primary=\"{info_result['stderr']}\", fallback=\"{pid_result['stderr']}\""
    )


def resetSocketState():
    global socketName, socketPath, serverPid, isInitializing, initPromise
    global tmuxAvailabilityChecked, tmuxAvailable, tmuxToolUsed
    socketName = None
    socketPath = None
    serverPid = None
    isInitializing = False
    initPromise = None
    tmuxAvailabilityChecked = False
    tmuxAvailable = False
    tmuxToolUsed = False


exec_tmux = execTmux
get_vivian_socket_name = getvivianSocketName
get_vivian_socket_path = getvivianSocketPath
set_vivian_socket_info = setvivianSocketInfo
is_socket_initialized = isSocketInitialized
get_vivian_tmux_env = getvivianTmuxEnv
check_tmux_available = checkTmuxAvailable
is_tmux_available = isTmuxAvailable
mark_tmux_tool_used = markTmuxToolUsed
has_tmux_tool_been_used = hasTmuxToolBeenUsed
ensure_socket_initialized = ensureSocketInitialized
kill_tmux_server = killTmuxServer
do_initialize = doInitialize
reset_socket_state = resetSocketState


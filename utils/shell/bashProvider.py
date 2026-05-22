"""Port of src/utils/shell/bashProvider.ts."""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass

from ..bash.bashPipeCommand import rearrangePipeCommand
from ..bash.ShellSnapshot import createAndSaveSnapshot
from ..bash.shellPrefix import formatShellPrefixCommand
from ..bash.shellQuote import quote
from ..bash.shellQuoting import (
    quoteShellCommand,
    rewriteWindowsNullRedirect,
    shouldAddStdinRedirect,
)
from ..debug import logForDebugging
from ..platform import get_platform
from ..sessionEnvironment import getSessionEnvironmentScript
from ..sessionEnvVars import getSessionEnvVars
from ..tmuxSocket import ensureSocketInitialized, getvivianTmuxEnv, hasTmuxToolBeenUsed
from ..windowsPaths import windowsPathToPosixPath


def getDisableExtglobCommand(shellPath: str) -> str | None:
    """Returns a shell command to disable extended glob patterns for security.
Extended globs (bash extglob, zsh EXTENDED_GLOB) can be exploited via
malicious filenames that expand after our security validation.

When vivian_CODE_SHELL_PREFIX is set, the actual executing shell may differ
from shellPath (e.g., shellPath is zsh but the wrapper runs bash). In this
case, we include commands for BOTH shells. We redirect both stdout and stderr
to /dev/null because zsh's command_not_found_handler writes to STDOUT.

When no shell prefix is set, we use the appropriate command for the detected shell."""
    if os.environ.get("vivian_CODE_SHELL_PREFIX"):
        return "{ shopt -u extglob || setopt NO_EXTENDED_GLOB; } >/dev/null 2>&1 || true"
    if "bash" in shellPath:
        return "shopt -u extglob 2>/dev/null || true"
    if "zsh" in shellPath:
        return "setopt NO_EXTENDED_GLOB 2>/dev/null || true"
    return None


@dataclass
class _BashShellProvider:
    shellPath: str
    skipSnapshot: bool = False
    type: str = "bash"
    detached: bool = True
    currentSandboxTmpDir: str | None = None
    lastSnapshotFilePath: str | None = None
    _snapshotPromise: object | None = None

    async def _get_snapshot_path(self) -> str | None:
        if self._snapshotPromise is None:
            if self.skipSnapshot:
                self._snapshotPromise = False
            else:
                try:
                    self._snapshotPromise = await createAndSaveSnapshot(self.shellPath)
                except Exception as error:
                    logForDebugging(f"Failed to create shell snapshot: {error}")
                    self._snapshotPromise = False
        return self._snapshotPromise or None

    async def buildExecCommand(self, command: str, opts: dict) -> dict[str, str]:
        snapshot_file_path = await self._get_snapshot_path()
        if snapshot_file_path and not os.path.exists(snapshot_file_path):
            logForDebugging(
                f"Snapshot file missing, falling back to login shell: {snapshot_file_path}"
            )
            snapshot_file_path = None
        self.lastSnapshotFilePath = snapshot_file_path
        self.currentSandboxTmpDir = opts.get("sandboxTmpDir")

        tmpdir = tempfile.gettempdir()
        is_windows = get_platform() == "windows"
        shell_tmpdir = windowsPathToPosixPath(tmpdir) if is_windows else tmpdir

        shell_cwd_file_path = (
            os.path.join(opts["sandboxTmpDir"], f"cwd-{opts['id']}")
            if opts.get("useSandbox")
            else os.path.join(shell_tmpdir, f"vivian-{opts['id']}-cwd")
        )
        cwd_file_path = (
            os.path.join(opts["sandboxTmpDir"], f"cwd-{opts['id']}")
            if opts.get("useSandbox")
            else os.path.join(tmpdir, f"vivian-{opts['id']}-cwd")
        )

        normalized_command = rewriteWindowsNullRedirect(command)
        add_stdin_redirect = shouldAddStdinRedirect(normalized_command)
        quoted_command = quoteShellCommand(normalized_command, add_stdin_redirect)
        if "|" in normalized_command and add_stdin_redirect:
            quoted_command = rearrangePipeCommand(normalized_command)

        command_parts: list[str] = []
        if snapshot_file_path:
            final_path = windowsPathToPosixPath(snapshot_file_path) if is_windows else snapshot_file_path
            command_parts.append(f"source {quote([final_path])} 2>/dev/null || true")

        session_env_script = await getSessionEnvironmentScript()
        if session_env_script:
            command_parts.append(session_env_script)

        disable_extglob_cmd = getDisableExtglobCommand(self.shellPath)
        if disable_extglob_cmd:
            command_parts.append(disable_extglob_cmd)

        command_parts.append(f"eval {quoted_command}")
        command_parts.append(f"pwd -P >| {quote([shell_cwd_file_path])}")
        command_string = " && ".join(command_parts)

        shell_prefix = os.environ.get("vivian_CODE_SHELL_PREFIX")
        if shell_prefix:
            command_string = formatShellPrefixCommand(shell_prefix, command_string)

        return {"commandString": command_string, "cwdFilePath": cwd_file_path}

    def getSpawnArgs(self, commandString: str) -> list[str]:
        skip_login_shell = self.lastSnapshotFilePath is not None
        if skip_login_shell:
            logForDebugging("Spawning shell without login (-l flag skipped)")
        return ["-c", *([] if skip_login_shell else ["-l"]), commandString]

    async def getEnvironmentOverrides(self, command: str) -> dict[str, str]:
        command_uses_tmux = "tmux" in command
        if os.environ.get("USER_TYPE") == "ant" and (hasTmuxToolBeenUsed() or command_uses_tmux):
            await ensureSocketInitialized()
        vivian_tmux_env = getvivianTmuxEnv()
        env: dict[str, str] = {}
        if vivian_tmux_env:
            env["TMUX"] = vivian_tmux_env
        if self.currentSandboxTmpDir:
            posix_tmp_dir = self.currentSandboxTmpDir
            if get_platform() == "windows":
                posix_tmp_dir = windowsPathToPosixPath(posix_tmp_dir)
            env["TMPDIR"] = posix_tmp_dir
            env["vivian_CODE_TMPDIR"] = posix_tmp_dir
            env["TMPPREFIX"] = os.path.join(posix_tmp_dir, "zsh")
        for key, value in getSessionEnvVars():
            env[key] = value
        return env


async def createBashShellProvider(shellPath: str, options: dict | None = None) -> _BashShellProvider:
    return _BashShellProvider(shellPath=shellPath, skipSnapshot=bool((options or {}).get("skipSnapshot")))

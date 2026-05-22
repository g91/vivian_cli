"""Port of src/utils/shell/powershellProvider.ts."""
from __future__ import annotations

import base64
import os
import tempfile
from dataclasses import dataclass

from ..sessionEnvVars import getSessionEnvVars


def buildPowerShellArgs(cmd: str) -> list[str]:
    return ["-NoProfile", "-NonInteractive", "-Command", cmd]


def encodePowerShellCommand(psCommand: str) -> str:
    return base64.b64encode(psCommand.encode("utf-16le")).decode("ascii")


@dataclass
class _PowerShellProvider:
    shellPath: str
    type: str = "powershell"
    detached: bool = False
    currentSandboxTmpDir: str | None = None

    async def buildExecCommand(self, command: str, opts: dict) -> dict[str, str]:
        self.currentSandboxTmpDir = opts.get("sandboxTmpDir") if opts.get("useSandbox") else None
        cwd_file_path = (
            os.path.join(opts["sandboxTmpDir"], f"vivian-pwd-ps-{opts['id']}")
            if opts.get("useSandbox") and opts.get("sandboxTmpDir")
            else os.path.join(tempfile.gettempdir(), f"vivian-pwd-ps-{opts['id']}")
        )
        escaped_cwd_file_path = cwd_file_path.replace("'", "''")
        cwd_tracking = (
            "\n; $_ec = if ($null -ne $LASTEXITCODE) { $LASTEXITCODE } elseif ($?) { 0 } else { 1 }"
            f"\n; (Get-Location).Path | Out-File -FilePath '{escaped_cwd_file_path}' -Encoding utf8 -NoNewline"
            "\n; exit $_ec"
        )
        ps_command = command + cwd_tracking
        if opts.get("useSandbox"):
            quoted_shell = self.shellPath.replace("'", "'\\''")
            command_string = " ".join([
                f"'{quoted_shell}'",
                "-NoProfile",
                "-NonInteractive",
                "-EncodedCommand",
                encodePowerShellCommand(ps_command),
            ])
        else:
            command_string = ps_command
        return {"commandString": command_string, "cwdFilePath": cwd_file_path}

    def getSpawnArgs(self, commandString: str) -> list[str]:
        return buildPowerShellArgs(commandString)

    async def getEnvironmentOverrides(self, command: str = "") -> dict[str, str]:
        del command
        env: dict[str, str] = {}
        for key, value in getSessionEnvVars():
            env[key] = value
        if self.currentSandboxTmpDir:
            env["TMPDIR"] = self.currentSandboxTmpDir
            env["vivian_CODE_TMPDIR"] = self.currentSandboxTmpDir
        return env


def createPowerShellProvider(shellPath: str) -> _PowerShellProvider:
    return _PowerShellProvider(shellPath=shellPath)

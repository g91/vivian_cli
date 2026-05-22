"""Port of src/utils/swarm/backends/it2Setup.ts."""
from __future__ import annotations

import os
from pathlib import Path

from ...config import get_global_config, save_global_config
from ...debug import logForDebugging
from ...execFileNoThrow import exec_file_no_throw
from ...log import logError


PythonPackageManager = str
It2InstallResult = dict[str, object]
It2VerifyResult = dict[str, object]


async def detectPythonPackageManager() -> PythonPackageManager | None:
    uv_result = await exec_file_no_throw("which", ["uv"])
    if uv_result.get("code") == 0:
        logForDebugging("[it2Setup] Found uv (will use uv tool install)")
        return "uvx"

    pipx_result = await exec_file_no_throw("which", ["pipx"])
    if pipx_result.get("code") == 0:
        logForDebugging("[it2Setup] Found pipx package manager")
        return "pipx"

    pip_result = await exec_file_no_throw("which", ["pip"])
    if pip_result.get("code") == 0:
        logForDebugging("[it2Setup] Found pip package manager")
        return "pip"

    pip3_result = await exec_file_no_throw("which", ["pip3"])
    if pip3_result.get("code") == 0:
        logForDebugging("[it2Setup] Found pip3 package manager")
        return "pip"

    logForDebugging("[it2Setup] No Python package manager found")
    return None


async def isIt2CliAvailable() -> bool:
    result = await exec_file_no_throw("which", ["it2"])
    return result.get("code") == 0


async def installIt2(packageManager: PythonPackageManager) -> It2InstallResult:
    logForDebugging(f"[it2Setup] Installing it2 using {packageManager}")
    home_dir = str(Path.home())

    if packageManager == "uvx":
        result = await exec_file_no_throw("uv", ["tool", "install", "it2"], cwd=home_dir)
    elif packageManager == "pipx":
        result = await exec_file_no_throw("pipx", ["install", "it2"], cwd=home_dir)
    else:
        result = await exec_file_no_throw("pip", ["install", "--user", "it2"], cwd=home_dir)
        if result.get("code") != 0:
            result = await exec_file_no_throw("pip3", ["install", "--user", "it2"], cwd=home_dir)

    if result.get("code") != 0:
        error = str(result.get("stderr") or "Unknown installation error")
        logError(RuntimeError(f"[it2Setup] Failed to install it2: {error}"))
        return {"success": False, "error": error, "packageManager": packageManager}

    logForDebugging("[it2Setup] it2 installed successfully")
    return {"success": True, "packageManager": packageManager}


async def verifyIt2Setup() -> It2VerifyResult:
    logForDebugging("[it2Setup] Verifying it2 setup...")
    installed = await isIt2CliAvailable()
    if not installed:
        return {"success": False, "error": "it2 CLI is not installed or not in PATH"}

    result = await exec_file_no_throw("it2", ["session", "list"])
    if result.get("code") != 0:
        stderr = str(result.get("stderr") or "").lower()
        if (
            "api" in stderr
            or "python" in stderr
            or "connection refused" in stderr
            or "not enabled" in stderr
        ):
            logForDebugging("[it2Setup] Python API not enabled in iTerm2")
            return {
                "success": False,
                "error": "Python API not enabled in iTerm2 preferences",
                "needsPythonApiEnabled": True,
            }
        return {
            "success": False,
            "error": str(result.get("stderr") or "Failed to communicate with iTerm2"),
        }

    logForDebugging("[it2Setup] it2 setup verified successfully")
    return {"success": True}


def getPythonApiInstructions() -> list[str]:
    return [
        "Almost done! Enable the Python API in iTerm2:",
        "",
        "  iTerm2 -> Settings -> General -> Magic -> Enable Python API",
        "",
        "After enabling, you may need to restart iTerm2.",
    ]


def markIt2SetupComplete() -> None:
    config = get_global_config()
    if config.get("iterm2It2SetupComplete") is not True:
        save_global_config(lambda current: {**current, "iterm2It2SetupComplete": True})
        logForDebugging("[it2Setup] Marked it2 setup as complete")


def setPreferTmuxOverIterm2(prefer: bool) -> None:
    config = get_global_config()
    if config.get("preferTmuxOverIterm2") != prefer:
        save_global_config(lambda current: {**current, "preferTmuxOverIterm2": prefer})
        logForDebugging(f"[it2Setup] Set preferTmuxOverIterm2 = {prefer}")


def getPreferTmuxOverIterm2() -> bool:
    config = get_global_config()
    return bool(config.get("preferTmuxOverIterm2"))


detect_python_package_manager = detectPythonPackageManager
is_it2_cli_available = isIt2CliAvailable
install_it2 = installIt2
verify_it2_setup = verifyIt2Setup
get_python_api_instructions = getPythonApiInstructions
mark_it2_setup_complete = markIt2SetupComplete
set_prefer_tmux_over_iterm2 = setPreferTmuxOverIterm2
get_prefer_tmux_over_iterm2 = getPreferTmuxOverIterm2
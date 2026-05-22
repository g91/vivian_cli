"""Port of src/utils/deepLink/terminalLauncher.ts."""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ..config import get_global_config
from ..debug import logForDebugging
from ..which import which


@dataclass(slots=True)
class TerminalInfo:
    name: str
    command: str


MACOS_TERMINALS = [
    {"name": "iTerm2", "bundleId": "com.googlecode.iterm2", "app": "iTerm"},
    {"name": "Ghostty", "bundleId": "com.mitchellh.ghostty", "app": "Ghostty"},
    {"name": "Kitty", "bundleId": "net.kovidgoyal.kitty", "app": "kitty"},
    {"name": "Alacritty", "bundleId": "org.alacritty", "app": "Alacritty"},
    {"name": "WezTerm", "bundleId": "com.github.wez.wezterm", "app": "WezTerm"},
    {"name": "Terminal.app", "bundleId": "com.apple.Terminal", "app": "Terminal"},
]
LINUX_TERMINALS = [
    "ghostty",
    "kitty",
    "alacritty",
    "wezterm",
    "gnome-terminal",
    "konsole",
    "xfce4-terminal",
    "mate-terminal",
    "tilix",
    "xterm",
]


async def detectMacosTerminal():
    stored = get_global_config().get("deepLinkTerminal")
    if stored:
        match = next((t for t in MACOS_TERMINALS if t["app"] == stored), None)
        if match:
            return TerminalInfo(match["name"], match["app"])
    term_program = os.environ.get("TERM_PROGRAM")
    if term_program:
        normalized = term_program.removesuffix(".app").lower()
        match = next((t for t in MACOS_TERMINALS if t["app"].lower() == normalized or t["name"].lower() == normalized), None)
        if match:
            return TerminalInfo(match["name"], match["app"])
    for terminal in MACOS_TERMINALS:
        if Path(f"/Applications/{terminal['app']}.app").exists():
            return TerminalInfo(terminal["name"], terminal["app"])
    return TerminalInfo("Terminal.app", "Terminal")


async def detectLinuxTerminal():
    term_env = os.environ.get("TERMINAL")
    if term_env:
        resolved = await which(term_env)
        if resolved:
            return TerminalInfo(Path(term_env).name, resolved)
    xte = await which("x-terminal-emulator")
    if xte:
        return TerminalInfo("x-terminal-emulator", xte)
    for terminal in LINUX_TERMINALS:
        resolved = await which(terminal)
        if resolved:
            return TerminalInfo(terminal, resolved)
    return None


async def detectWindowsTerminal():
    for name in ("wt.exe", "pwsh.exe", "powershell.exe"):
        resolved = await which(name)
        if resolved:
            if name == "wt.exe":
                return TerminalInfo("Windows Terminal", resolved)
            return TerminalInfo("PowerShell", resolved)
    return TerminalInfo("Command Prompt", "cmd.exe")


async def detectTerminal():
    if sys.platform == "darwin":
        return await detectMacosTerminal()
    if sys.platform == "linux":
        return await detectLinuxTerminal()
    if sys.platform == "win32":
        return await detectWindowsTerminal()
    return None


async def launchInTerminal(vivianPath, action=None):
    terminal = await detectTerminal()
    if not terminal:
        logForDebugging("No terminal emulator detected", level="error")
        return False
    action = action or {}
    logForDebugging(f"Launching in terminal: {terminal.name} ({terminal.command})")
    vivian_args = ["--deep-link-origin"]
    if action.get("repo"):
        vivian_args.extend(["--deep-link-repo", str(action["repo"])])
        if action.get("lastFetchMs") is not None:
            vivian_args.extend(["--deep-link-last-fetch", str(action["lastFetchMs"])])
    if action.get("query"):
        vivian_args.extend(["--prefill", str(action["query"])])
    if sys.platform == "darwin":
        return await launchMacosTerminal(terminal, vivianPath, vivian_args, action.get("cwd"))
    if sys.platform == "linux":
        return await launchLinuxTerminal(terminal, vivianPath, vivian_args, action.get("cwd"))
    if sys.platform == "win32":
        return await launchWindowsTerminal(terminal, vivianPath, vivian_args, action.get("cwd"))
    return False


async def launchMacosTerminal(terminal, vivianPath, vivianArgs, cwd=None):
    command = buildShellCommand(vivianPath, vivianArgs, cwd)
    if terminal.command == "Terminal":
        script = f'tell application "Terminal"\n  do script {appleScriptQuote(command)}\n  activate\nend tell'
    else:
        script = (
            'tell application "iTerm"\n'
            '  if running then\n    create window with default profile\n  else\n    activate\n  end if\n'
            f'  tell current session of current window\n    write text {appleScriptQuote(command)}\n  end tell\nend tell'
        )
    proc = await asyncio.create_subprocess_exec("osascript", "-e", script)
    return await proc.wait() == 0


async def launchLinuxTerminal(terminal, vivianPath, vivianArgs, cwd=None):
    spawn_cwd = None
    if terminal.name == "gnome-terminal":
        args = [f"--working-directory={cwd}", "--"] if cwd else ["--"]
        args.extend([vivianPath, *vivianArgs])
    elif terminal.name == "konsole":
        args = ["--workdir", cwd, "-e"] if cwd else ["-e"]
        args.extend([vivianPath, *vivianArgs])
    elif terminal.name == "kitty":
        args = (["--directory", cwd] if cwd else []) + [vivianPath, *vivianArgs]
    elif terminal.name == "wezterm":
        args = (["start", "--cwd", cwd, "--"] if cwd else ["start", "--"]) + [vivianPath, *vivianArgs]
    elif terminal.name == "alacritty":
        args = (["--working-directory", cwd, "-e"] if cwd else ["-e"]) + [vivianPath, *vivianArgs]
    elif terminal.name == "ghostty":
        args = ([f"--working-directory={cwd}", "-e"] if cwd else ["-e"]) + [vivianPath, *vivianArgs]
    elif terminal.name in {"xfce4-terminal", "mate-terminal"}:
        args = ([f"--working-directory={cwd}", "-x"] if cwd else ["-x"]) + [vivianPath, *vivianArgs]
    elif terminal.name == "tilix":
        args = ([f"--working-directory={cwd}", "-e"] if cwd else ["-e"]) + [vivianPath, *vivianArgs]
    else:
        args = ["-e", vivianPath, *vivianArgs]
        spawn_cwd = cwd
    return spawnDetached(terminal.command, args, {"cwd": spawn_cwd})


async def launchWindowsTerminal(terminal, vivianPath, vivianArgs, cwd=None):
    if terminal.name == "Windows Terminal":
        args = (["-d", cwd] if cwd else []) + ["--", vivianPath, *vivianArgs]
        return spawnDetached(terminal.command, args)
    if terminal.name == "PowerShell":
        cd_cmd = f"Set-Location {psQuote(cwd)}; " if cwd else ""
        args = ["-NoExit", "-Command", f"{cd_cmd}& {psQuote(vivianPath)} {' '.join(psQuote(a) for a in vivianArgs)}"]
        return spawnDetached(terminal.command, args)
    cd_cmd = f"cd /d {cmdQuote(cwd)} && " if cwd else ""
    args = ["/k", f"{cd_cmd}{cmdQuote(vivianPath)} {' '.join(cmdQuote(a) for a in vivianArgs)}"]
    return spawnDetached(terminal.command, args, {"windowsVerbatimArguments": True})


def spawnDetached(command, args, opts={}):
    try:
        kwargs = {"cwd": opts.get("cwd")}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(
            [command, *args],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            **kwargs,
        )
        return proc.poll() is None or proc.returncode == 0
    except Exception as err:
        logForDebugging(f"Failed to spawn {command}: {err}", level="error")
        return False


def buildShellCommand(vivianPath, vivianArgs, cwd=None):
    cd_prefix = f"cd {shellQuote(cwd)} && " if cwd else ""
    return cd_prefix + " ".join(shellQuote(part) for part in [vivianPath, *vivianArgs])


def shellQuote(s):
    return "'" + str(s).replace("'", "'\\''") + "'"


def appleScriptQuote(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def psQuote(s):
    return "'" + str(s).replace("'", "''") + "'"


def cmdQuote(arg):
    stripped = str(arg).replace('"', "").replace("%", "%%")
    trailing_backslashes = len(stripped) - len(stripped.rstrip("\\"))
    escaped = stripped.rstrip("\\") + ("\\" * (trailing_backslashes * 2))
    return f'"{escaped}"'


detect_macos_terminal = detectMacosTerminal
detect_linux_terminal = detectLinuxTerminal
detect_windows_terminal = detectWindowsTerminal
detect_terminal = detectTerminal
launch_in_terminal = launchInTerminal
launch_macos_terminal = launchMacosTerminal
launch_linux_terminal = launchLinuxTerminal
launch_windows_terminal = launchWindowsTerminal
spawn_detached = spawnDetached
build_shell_command = buildShellCommand
shell_quote = shellQuote
apple_script_quote = appleScriptQuote
ps_quote = psQuote
cmd_quote = cmdQuote


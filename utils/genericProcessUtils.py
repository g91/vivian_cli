"""Port of src/utils/genericProcessUtils.ts."""
from __future__ import annotations

from typing import List, Optional
import os
import subprocess
import asyncio

from .execFileNoThrow import exec_file_no_throw, exec_file_no_throw_sync


def isProcessRunning(pid):
    """Check if a process with the given PID is running (signal 0 probe).

PID ≤ 1 returns false (0 is current process group, 1 is init).

Note: `process.kill(pid, 0)` throws EPERM when the process exists but is
owned by another user. This reports such processes as NOT running, which
is conservative for lock recovery (we won't steal a live lock)."""
    if int(pid) <= 1:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


async def getAncestorPidsAsync(pid, maxDepth = 10):
    """Gets the ancestor process chain for a given process (up to maxDepth levels)
@param pid - The starting process ID
@param maxDepth - Maximum number of ancestors to fetch (default: 10)
@returns Array of ancestor PIDs from immediate parent to furthest ancestor"""
    pid_str = str(pid)
    if os.name == "nt":
        script = (
            f"$pid = {pid_str}; "
            f"$ancestors = @(); "
            f"for ($i = 0; $i -lt {maxDepth}; $i++) {{ "
            '  $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$pid" -ErrorAction SilentlyContinue; '
            '  if (-not $proc -or -not $proc.ParentProcessId -or $proc.ParentProcessId -eq 0) { break }; '
            '  $pid = $proc.ParentProcessId; '
            '  $ancestors += $pid; '
            '}; '
            '$ancestors -join ","'
        )
        result = await exec_file_no_throw("powershell.exe", ["-NoProfile", "-Command", script], timeout=3)
        if result.get("code") != 0 or not (result.get("stdout") or "").strip():
            return []
        return [
            int(part)
            for part in result["stdout"].strip().split(",")
            if part and part.isdigit()
        ]

    script = (
        f"pid={pid_str}; "
        f"for i in $(seq 1 {maxDepth}); do "
        "ppid=$(ps -o ppid= -p $pid 2>/dev/null | tr -d ' '); "
        'if [ -z "$ppid" ] || [ "$ppid" = "0" ] || [ "$ppid" = "1" ]; then break; fi; '
        'echo $ppid; pid=$ppid; '
        "done"
    )
    result = await exec_file_no_throw("sh", ["-c", script], timeout=3)
    if result.get("code") != 0 or not (result.get("stdout") or "").strip():
        return []
    output = []
    for part in result["stdout"].strip().splitlines():
        try:
            output.append(int(part))
        except ValueError:
            continue
    return output


def getProcessCommand(pid):
    """Gets the command line for a given process
@param pid - The process ID to get the command for
@returns The command line string, or null if not found
@deprecated Use getAncestorCommandsAsync instead"""
    try:
        pid_str = str(pid)
        if os.name == "nt":
            result = exec_file_no_throw_sync(
                "powershell.exe",
                [
                    "-NoProfile",
                    "-Command",
                    f'(Get-CimInstance Win32_Process -Filter "ProcessId={pid_str}").CommandLine',
                ],
                timeout=1,
            )
        else:
            result = exec_file_no_throw_sync("ps", ["-o", "command=", "-p", pid_str], timeout=1)
        stdout = (result.get("stdout") or "").strip()
        return stdout or None
    except Exception:
        return None


async def getAncestorCommandsAsync(pid, maxDepth = 10):
    """Gets the command lines for a process and its ancestors in a single call
@param pid - The starting process ID
@param maxDepth - Maximum depth to traverse (default: 10)
@returns Array of command strings for the process chain"""
    pid_str = str(pid)
    if os.name == "nt":
        script = (
            f"$currentPid = {pid_str}; "
            f"$commands = @(); "
            f"for ($i = 0; $i -lt {maxDepth}; $i++) {{ "
            '  $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$currentPid" -ErrorAction SilentlyContinue; '
            '  if (-not $proc) { break }; '
            '  if ($proc.CommandLine) { $commands += $proc.CommandLine }; '
            '  if (-not $proc.ParentProcessId -or $proc.ParentProcessId -eq 0) { break }; '
            '  $currentPid = $proc.ParentProcessId; '
            '}; '
            '$commands -join [char]0'
        )
        result = await exec_file_no_throw("powershell.exe", ["-NoProfile", "-Command", script], timeout=3)
        if result.get("code") != 0 or not (result.get("stdout") or "").strip():
            return []
        return [part for part in result["stdout"].split("\0") if part]

    script = (
        f"currentpid={pid_str}; "
        f"for i in $(seq 1 {maxDepth}); do "
        "cmd=$(ps -o command= -p $currentpid 2>/dev/null); "
        "if [ -n \"$cmd\" ]; then printf '%s\\0' \"$cmd\"; fi; "
        "ppid=$(ps -o ppid= -p $currentpid 2>/dev/null | tr -d ' '); "
        'if [ -z "$ppid" ] || [ "$ppid" = "0" ] || [ "$ppid" = "1" ]; then break; fi; '
        "currentpid=$ppid; "
        "done"
    )
    result = await exec_file_no_throw("sh", ["-c", script], timeout=3)
    if result.get("code") != 0 or not (result.get("stdout") or ""):
        return []
    return [part for part in result["stdout"].split("\0") if part]


def getChildPids(pid):
    """Gets the child process IDs for a given process
@param pid - The parent process ID
@returns Array of child process IDs as numbers"""
    try:
        pid_str = str(pid)
        if os.name == "nt":
            result = exec_file_no_throw_sync(
                "powershell.exe",
                [
                    "-NoProfile",
                    "-Command",
                    f'(Get-CimInstance Win32_Process -Filter "ParentProcessId={pid_str}").ProcessId',
                ],
                timeout=1,
            )
        else:
            result = exec_file_no_throw_sync("pgrep", ["-P", pid_str], timeout=1)
        stdout = (result.get("stdout") or "").strip()
        if not stdout:
            return []
        children = []
        for part in stdout.splitlines():
            try:
                children.append(int(part))
            except ValueError:
                continue
        return children
    except Exception:
        return []


is_process_running = isProcessRunning
get_ancestor_pids_async = getAncestorPidsAsync
get_process_command = getProcessCommand
get_ancestor_commands_async = getAncestorCommandsAsync
get_child_pids = getChildPids


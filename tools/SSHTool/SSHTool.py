"""
SSHTool — SSH into remote servers for administration and security testing.

Provides persistent SSH connections with command execution, file transfer,
and session management. Useful for server administration, CTF challenges,
and remote vulnerability assessment.
"""
from __future__ import annotations

import asyncio
import os
import re
import subprocess
import tempfile
import json
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional

TOOL_NAME = "SSH"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["command"],
    "properties": {
        "command": {
            "type": "string",
            "description": (
                "The SSH-related command to execute. One of:\n"
                "- 'connect <host>' — Connect to a remote host (prompts for credentials)\n"
                "- 'exec <command>' — Execute a command on the connected host\n"
                "- 'disconnect' — Close the current SSH connection\n"
                "- 'status' — Show current connection status\n"
                "- 'upload <local_path> <remote_path>' — Upload a file via SCP\n"
                "- 'download <remote_path> <local_path>' — Download a file via SCP\n"
                "- 'port_forward <local_port> <remote_host> <remote_port>' — Set up SSH port forwarding\n"
                "- 'scan_ports <host> [ports]' — Quick port scan via SSH (requires nc on remote)\n"
                "- 'check_sudo' — Check if the connected user has sudo access\n"
                "- 'find_suid' — Find SUID binaries on the remote system\n"
                "- 'enum_system' — Basic system enumeration (OS, kernel, users, services)"
            ),
        },
        "host": {
            "type": "string",
            "description": "Remote hostname or IP address for connect command.",
        },
        "port": {
            "type": "integer",
            "description": "SSH port (default: 22).",
            "default": 22,
        },
        "username": {
            "type": "string",
            "description": "SSH username for connect command.",
        },
        "password": {
            "type": "string",
            "description": "SSH password (use key-based auth when possible).",
        },
        "key_file": {
            "type": "string",
            "description": "Path to SSH private key file.",
        },
        "timeout": {
            "type": "number",
            "description": "Command timeout in milliseconds (default: 30000).",
            "default": 30000,
        },
        "description": {
            "type": "string",
            "description": "Clear, concise description of what this SSH operation does.",
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "stdout": {"type": "string", "description": "Standard output from the SSH command."},
        "stderr": {"type": "string", "description": "Standard error from the SSH command."},
        "exit_code": {"type": "integer", "description": "Exit code of the remote command."},
        "connected": {"type": "boolean", "description": "Whether an SSH session is currently active."},
        "host": {"type": "string", "description": "Currently connected host, if any."},
        "interrupted": {"type": "boolean", "description": "Whether the command was interrupted."},
    },
}

# ── Session state (module-level, persists across calls) ─────────────────────
_session: Dict[str, Any] = {
    "connected": False,
    "host": None,
    "port": 22,
    "username": None,
    "identity_file": None,
    "control_path": None,
}


def _get_control_path() -> str:
    """Get a unique control path for SSH multiplexing."""
    if _session["control_path"]:
        return _session["control_path"]
    path = os.path.join(tempfile.gettempdir(), f"vivian_ssh_{os.getpid()}")
    _session["control_path"] = path
    return path


def _build_ssh_base_args() -> List[str]:
    """Build base SSH arguments using the current session state."""
    args = ["ssh"]
    control_path = _get_control_path()

    if _session["connected"]:
        args.extend([
            "-o", f"ControlPath={control_path}",
            "-o", "ControlMaster=auto",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "ConnectTimeout=10",
            "-o", "ServerAliveInterval=30",
        ])
        if _session["port"] and _session["port"] != 22:
            args.extend(["-p", str(_session["port"])])
        if _session["identity_file"]:
            args.extend(["-i", _session["identity_file"]])
        if _session["username"]:
            args.append(f"{_session['username']}@{_session['host']}")
        else:
            args.append(_session["host"])

    return args


async def _run_ssh(args: List[str], timeout_ms: int = 30000, input_data: Optional[str] = None) -> Dict[str, Any]:
    """Run an SSH command and return structured output."""
    try:
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                *args,
                stdin=asyncio.subprocess.PIPE if input_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            ),
            timeout=10,
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input_data.encode() if input_data else None),
            timeout=timeout_ms / 1000.0,
        )

        return {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "exit_code": proc.returncode or 0,
            "connected": _session["connected"],
            "host": _session["host"],
            "interrupted": False,
        }
    except asyncio.TimeoutError:
        return {
            "stdout": "",
            "stderr": "SSH command timed out.",
            "exit_code": -1,
            "connected": _session["connected"],
            "host": _session["host"],
            "interrupted": True,
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"SSH error: {str(e)}",
            "exit_code": -1,
            "connected": _session["connected"],
            "host": _session["host"],
            "interrupted": False,
        }


async def _cmd_connect(args: Dict[str, Any]) -> Dict[str, Any]:
    """Establish an SSH connection."""
    host = args.get("host", "").strip()
    if not host:
        return {"stdout": "", "stderr": "No host specified.", "exit_code": -1,
                "connected": False, "host": None, "interrupted": False}

    port = args.get("port", 22)
    username = args.get("username", "").strip()
    password = args.get("password", "").strip()
    key_file = args.get("key_file", "").strip()

    _session["host"] = host
    _session["port"] = port
    _session["username"] = username or None
    _session["identity_file"] = key_file or None

    ssh_args = [
        "ssh", "-o", "ControlMaster=auto",
        "-o", f"ControlPath={_get_control_path()}",
        "-o", "ControlPersist=60",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ConnectTimeout=10",
        "-o", "BatchMode=yes" if not password else "BatchMode=no",
    ]

    if port != 22:
        ssh_args.extend(["-p", str(port)])
    if key_file:
        ssh_args.extend(["-i", key_file])

    target = f"{username}@{host}" if username else host
    ssh_args.extend([target, "echo", "SSH_CONNECTION_OK"])

    # If password provided, use sshpass
    if password:
        ssh_args = ["sshpass", "-p", password] + ssh_args

    result = await _run_ssh(ssh_args, timeout_ms=args.get("timeout", 15000))

    if "SSH_CONNECTION_OK" in result["stdout"]:
        _session["connected"] = True
        result["connected"] = True
        result["stdout"] = f"Connected to {host}" + (f" as {username}" if username else "") + "\n" + result["stdout"]
    else:
        _session["connected"] = False
        result["connected"] = False
        result["stderr"] = f"Failed to connect to {host}: " + (result["stderr"] or result["stdout"])

    return result


async def _cmd_exec(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a command on the connected host."""
    if not _session["connected"]:
        return {"stdout": "", "stderr": "Not connected to any host. Use 'connect' first.",
                "exit_code": -1, "connected": False, "host": None, "interrupted": False}

    command = args.get("command", "")
    # Extract the actual remote command (strip the 'exec' prefix)
    remote_cmd = command
    if command.lower().startswith("exec "):
        remote_cmd = command[5:].strip()

    if not remote_cmd:
        return {"stdout": "", "stderr": "No command specified for remote execution.",
                "exit_code": -1, "connected": True, "host": _session["host"], "interrupted": False}

    ssh_args = _build_ssh_base_args() + [remote_cmd]
    return await _run_ssh(ssh_args, timeout_ms=args.get("timeout", 30000))


async def _cmd_disconnect(args: Dict[str, Any]) -> Dict[str, Any]:
    """Close the SSH connection."""
    if _session["connected"]:
        ssh_args = ["ssh", "-O", "exit", "-o", f"ControlPath={_get_control_path()}",
                     f"{_session['username']}@{_session['host']}" if _session['username'] else _session['host']]
        await _run_ssh(ssh_args, timeout_ms=5000)

    _session["connected"] = False
    _session["host"] = None
    _session["port"] = 22
    _session["username"] = None
    _session["identity_file"] = None

    return {"stdout": "Disconnected.", "stderr": "", "exit_code": 0,
            "connected": False, "host": None, "interrupted": False}


async def _cmd_status(args: Dict[str, Any]) -> Dict[str, Any]:
    """Show current connection status."""
    if _session["connected"]:
        return {
            "stdout": f"Connected to {_session['host']}:{_session['port']}"
                      + (f" as {_session['username']}" if _session['username'] else ""),
            "stderr": "", "exit_code": 0,
            "connected": True, "host": _session["host"], "interrupted": False,
        }
    return {"stdout": "Not connected.", "stderr": "", "exit_code": 0,
            "connected": False, "host": None, "interrupted": False}


async def _cmd_scp(args: Dict[str, Any], direction: str) -> Dict[str, Any]:
    """Upload or download a file via SCP."""
    if not _session["connected"]:
        return {"stdout": "", "stderr": "Not connected to any host.",
                "exit_code": -1, "connected": False, "host": None, "interrupted": False}

    command = args.get("command", "")
    parts = shlex.split(command)

    if len(parts) < 3:
        return {"stdout": "", "stderr": f"Usage: {direction} <source> <dest>",
                "exit_code": -1, "connected": True, "host": _session["host"], "interrupted": False}

    local_path = parts[1]
    remote_path = parts[2]

    scp_args = ["scp", "-o", f"ControlPath={_get_control_path()}",
                "-o", "StrictHostKeyChecking=accept-new"]
    if _session["port"] and _session["port"] != 22:
        scp_args.extend(["-P", str(_session["port"])])
    if _session["identity_file"]:
        scp_args.extend(["-i", _session["identity_file"]])

    target = f"{_session['username']}@{_session['host']}" if _session['username'] else _session['host']

    if direction == "upload":
        scp_args.extend([local_path, f"{target}:{remote_path}"])
    else:
        scp_args.extend([f"{target}:{remote_path}", local_path])

    return await _run_ssh(scp_args, timeout_ms=args.get("timeout", 60000))


async def _cmd_port_forward(args: Dict[str, Any]) -> Dict[str, Any]:
    """Set up SSH port forwarding."""
    if not _session["connected"]:
        return {"stdout": "", "stderr": "Not connected to any host.",
                "exit_code": -1, "connected": False, "host": None, "interrupted": False}

    command = args.get("command", "")
    parts = shlex.split(command)

    if len(parts) < 4:
        return {"stdout": "", "stderr": "Usage: port_forward <local_port> <remote_host> <remote_port>",
                "exit_code": -1, "connected": True, "host": _session["host"], "interrupted": False}

    local_port = parts[1]
    remote_host = parts[2]
    remote_port = parts[3]

    ssh_args = _build_ssh_base_args() + [
        "-L", f"{local_port}:{remote_host}:{remote_port}",
        "-N",  # Don't execute remote command
    ]

    # Run in background
    result = await _run_ssh(ssh_args, timeout_ms=5000)
    result["stdout"] = f"Port forward: localhost:{local_port} -> {remote_host}:{remote_port} (via {_session['host']})\n" + result["stdout"]
    return result


async def _cmd_scan_ports(args: Dict[str, Any]) -> Dict[str, Any]:
    """Quick port scan from the remote host."""
    if not _session["connected"]:
        return {"stdout": "", "stderr": "Not connected to any host.",
                "exit_code": -1, "connected": False, "host": None, "interrupted": False}

    command = args.get("command", "")
    parts = shlex.split(command)

    if len(parts) < 2:
        return {"stdout": "", "stderr": "Usage: scan_ports <target_host> [port_range]",
                "exit_code": -1, "connected": True, "host": _session["host"], "interrupted": False}

    target = parts[1]
    port_range = parts[2] if len(parts) > 2 else "1-1000"

    # Use bash /dev/tcp or nc for port scanning
    scan_cmd = (
        f"for port in $(seq {port_range.replace('-', ' ')}); do "
        f"(echo >/dev/tcp/{target}/$port) 2>/dev/null && echo 'Port $port: OPEN'; "
        f"done"
    )

    ssh_args = _build_ssh_base_args() + ["bash", "-c", scan_cmd]
    return await _run_ssh(ssh_args, timeout_ms=args.get("timeout", 60000))


async def _cmd_check_sudo(args: Dict[str, Any]) -> Dict[str, Any]:
    """Check sudo access on remote host."""
    if not _session["connected"]:
        return {"stdout": "", "stderr": "Not connected to any host.",
                "exit_code": -1, "connected": False, "host": None, "interrupted": False}

    ssh_args = _build_ssh_base_args() + ["sudo", "-ln"]
    result = await _run_ssh(ssh_args, timeout_ms=10000)
    if result["exit_code"] != 0:
        result["stdout"] = "No sudo access or password required.\n" + result["stdout"]
    else:
        result["stdout"] = "SUDO ACCESS AVAILABLE:\n" + result["stdout"]
    return result


async def _cmd_find_suid(args: Dict[str, Any]) -> Dict[str, Any]:
    """Find SUID binaries on remote host."""
    if not _session["connected"]:
        return {"stdout": "", "stderr": "Not connected to any host.",
                "exit_code": -1, "connected": False, "host": None, "interrupted": False}

    ssh_args = _build_ssh_base_args() + [
        "find", "/", "-perm", "-4000", "-type", "f", "2>/dev/null"
    ]
    return await _run_ssh(ssh_args, timeout_ms=30000)


async def _cmd_enum_system(args: Dict[str, Any]) -> Dict[str, Any]:
    """Basic system enumeration."""
    if not _session["connected"]:
        return {"stdout": "", "stderr": "Not connected to any host.",
                "exit_code": -1, "connected": False, "host": None, "interrupted": False}

    enum_script = """
echo "=== OS Info ==="
cat /etc/os-release 2>/dev/null || cat /etc/*release 2>/dev/null
echo ""
echo "=== Kernel ==="
uname -a
echo ""
echo "=== Current User ==="
id
echo ""
echo "=== Users with shells ==="
grep -E '/bin/(ba|z|fi)?sh' /etc/passwd 2>/dev/null | cut -d: -f1
echo ""
echo "=== Listening Services ==="
ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null
echo ""
echo "=== Cron Jobs ==="
cat /etc/crontab 2>/dev/null
ls -la /etc/cron.* 2>/dev/null
echo ""
echo "=== SUID Binaries ==="
find / -perm -4000 -type f 2>/dev/null | head -20
echo ""
echo "=== Writable configs in /etc ==="
find /etc -writable -type f 2>/dev/null | head -20
echo ""
echo "=== Home directories ==="
ls -la /home/ 2>/dev/null
"""

    ssh_args = _build_ssh_base_args() + ["bash", "-c", enum_script]
    return await _run_ssh(ssh_args, timeout_ms=30000)


# ── Command dispatch ────────────────────────────────────────────────────────

_COMMAND_MAP = {
    "connect": _cmd_connect,
    "exec": _cmd_exec,
    "disconnect": _cmd_disconnect,
    "status": _cmd_status,
    "upload": lambda args: _cmd_scp(args, "upload"),
    "download": lambda args: _cmd_scp(args, "download"),
    "port_forward": _cmd_port_forward,
    "scan_ports": _cmd_scan_ports,
    "check_sudo": _cmd_check_sudo,
    "find_suid": _cmd_find_suid,
    "enum_system": _cmd_enum_system,
}


async def call(args: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
    """Main entry point for the SSH tool."""
    command = (args.get("command") or "").strip()

    if not command:
        return {"stdout": "", "stderr": "No SSH command specified. Use 'connect', 'exec', 'disconnect', 'status', etc.",
                "exit_code": -1, "connected": _session["connected"], "host": _session["host"], "interrupted": False}

    # Parse the sub-command
    parts = command.split(None, 1)
    sub_cmd = parts[0].lower()

    handler = _COMMAND_MAP.get(sub_cmd)
    if handler:
        return await handler(args)

    # If connected, treat unknown commands as remote exec
    if _session["connected"]:
        return await _cmd_exec(args)

    return {"stdout": "", "stderr": f"Unknown SSH command: '{sub_cmd}'. Available: {', '.join(_COMMAND_MAP)}",
            "exit_code": -1, "connected": False, "host": None, "interrupted": False}


async def description() -> str:
    return "SSH into remote servers for administration, file transfer, and security testing."


async def prompt() -> str:
    return (
        "Use this tool to SSH into remote servers. You can connect to hosts, execute commands, "
        "transfer files via SCP, set up port forwarding, and perform basic security enumeration. "
        "First connect with 'connect <host>', then use 'exec <command>' to run commands. "
        "Use 'enum_system' for quick reconnaissance, 'find_suid' to locate privilege escalation "
        "vectors, and 'scan_ports' to discover open ports from the remote host's perspective."
    )


def userFacingName() -> str:
    return "SSH"


def getToolUseSummary(input_data: Dict[str, Any]) -> str:
    cmd = input_data.get("command", "")
    if cmd.startswith("connect"):
        return f"SSH connect to {input_data.get('host', 'unknown')}"
    if cmd.startswith("exec"):
        return f"SSH exec: {cmd[5:60]}"
    return f"SSH: {cmd[:60]}"

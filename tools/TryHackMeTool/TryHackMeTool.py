"""
TryHackMeTool — Interact with TryHackMe CTF platform.

Supports connecting to TryHackMe VPN, managing room sessions,
running CTF enumeration workflows, and tracking flag captures.
"""
from __future__ import annotations

import asyncio
import os
import re
import subprocess
import json
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

TOOL_NAME = "TryHackMe"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["command"],
    "properties": {
        "command": {
            "type": "string",
            "description": (
                "The TryHackMe operation to perform. One of:\n"
                "- 'vpn_connect <config_path>' — Connect to TryHackMe via OpenVPN config\n"
                "- 'vpn_status' — Check VPN connection status\n"
                "- 'vpn_disconnect' — Disconnect from TryHackMe VPN\n"
                "- 'start_machine <ip>' — Start a TryHackMe machine (via web or assume running)\n"
                "- 'nmap_scan <target_ip> [options]' — Run nmap scan on target\n"
                "- 'gobuster <target_url> <wordlist>' — Directory enumeration with gobuster\n"
                "- 'nikto_scan <target_url>' — Web server vulnerability scan with nikto\n"
                "- 'hydra_brute <service> <target> <username> <wordlist>' — Brute force with hydra\n"
                "- 'enum4linux <target_ip>' — SMB/enum4linux enumeration\n"
                "- 'smb_client <target_ip> [share]' — SMB client operations\n"
                "- 'sqlmap <target_url>' — SQL injection testing with sqlmap\n"
                "- 'john_crack <hash_file> [wordlist]' — Crack hashes with John the Ripper\n"
                "- 'linpeas_upload <target_ip> [username]' — Upload and run linpeas on target\n"
                "- 'submit_flag <flag>' — Record a captured flag\n"
                "- 'flags_found' — List all flags found this session\n"
                "- 'room_info <room_name>' — Get info about a TryHackMe room\n"
                "- 'check_tools' — Check which CTF tools are available locally"
            ),
        },
        "target_ip": {
            "type": "string",
            "description": "Target IP address for scans and attacks.",
        },
        "target_url": {
            "type": "string",
            "description": "Target URL for web-based scans.",
        },
        "wordlist": {
            "type": "string",
            "description": "Path to wordlist file (e.g., /usr/share/wordlists/rockyou.txt).",
        },
        "username": {
            "type": "string",
            "description": "Username for brute force or authentication.",
        },
        "options": {
            "type": "string",
            "description": "Additional command-line options to pass to the tool.",
        },
        "timeout": {
            "type": "number",
            "description": "Command timeout in milliseconds (default: 120000).",
            "default": 120000,
        },
        "description": {
            "type": "string",
            "description": "Clear, concise description of what this CTF operation does.",
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "stdout": {"type": "string", "description": "Standard output from the CTF tool."},
        "stderr": {"type": "string", "description": "Standard error from the CTF tool."},
        "exit_code": {"type": "integer", "description": "Exit code of the command."},
        "flags_found": {"type": "array", "items": {"type": "string"}, "description": "Flags captured this session."},
        "vpn_connected": {"type": "boolean", "description": "Whether TryHackMe VPN is connected."},
        "interrupted": {"type": "boolean", "description": "Whether the command was interrupted."},
    },
}

# ── Session state ───────────────────────────────────────────────────────────
_session: Dict[str, Any] = {
    "vpn_connected": False,
    "vpn_interface": "tun0",
    "flags_found": [],
    "current_target": None,
    "current_room": None,
}

# ── Common wordlists ────────────────────────────────────────────────────────
_COMMON_WORDLISTS = [
    "/usr/share/wordlists/rockyou.txt",
    "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt",
    "/usr/share/wordlists/dirb/common.txt",
    "/usr/share/seclists/Discovery/Web-Content/common.txt",
    "/usr/share/wordlists/dirb/big.txt",
]

# ── Tool availability ───────────────────────────────────────────────────────
_CTF_TOOLS = {
    "nmap": "nmap",
    "gobuster": "gobuster",
    "nikto": "nikto",
    "hydra": "hydra",
    "enum4linux": "enum4linux",
    "smbclient": "smbclient",
    "sqlmap": "sqlmap",
    "john": "john",
    "hashcat": "hashcat",
    "dirb": "dirb",
    "ffuf": "ffuf",
    "metasploit": "msfconsole",
    "netcat": "nc",
    "socat": "socat",
    "python3": "python3",
    "curl": "curl",
    "wget": "wget",
    "openvpn": "openvpn",
}


async def _run_command(cmd: List[str], timeout_ms: int = 120000, cwd: Optional[str] = None) -> Dict[str, Any]:
    """Run a local command and return structured output."""
    try:
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            ),
            timeout=10,
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout_ms / 1000.0,
        )

        return {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "exit_code": proc.returncode or 0,
            "interrupted": False,
        }
    except asyncio.TimeoutError:
        return {"stdout": "", "stderr": "Command timed out.", "exit_code": -1, "interrupted": True}
    except FileNotFoundError:
        return {"stdout": "", "stderr": f"Tool not found: {cmd[0]}. Install it first.", "exit_code": -1, "interrupted": False}
    except Exception as e:
        return {"stdout": "", "stderr": f"Error: {str(e)}", "exit_code": -1, "interrupted": False}


def _find_wordlist(preferred: Optional[str] = None) -> Optional[str]:
    """Find an available wordlist."""
    if preferred and os.path.exists(preferred):
        return preferred
    for wl in _COMMON_WORDLISTS:
        if os.path.exists(wl):
            return wl
    return None


# ── Command handlers ────────────────────────────────────────────────────────

async def _cmd_vpn_connect(args: Dict[str, Any]) -> Dict[str, Any]:
    """Connect to TryHackMe VPN."""
    config_path = args.get("command", "").replace("vpn_connect ", "", 1).strip()
    if not config_path:
        return _make_result("No OpenVPN config path provided. Usage: vpn_connect <path_to_.ovpn>", is_error=True)

    if not os.path.exists(config_path):
        return _make_result(f"OpenVPN config not found: {config_path}", is_error=True)

    # Run openvpn in background
    result = await _run_command(
        ["openvpn", "--config", config_path, "--daemon"],
        timeout_ms=10000,
    )

    if result["exit_code"] == 0:
        _session["vpn_connected"] = True
        result["stdout"] = "VPN connection initiated.\n" + result["stdout"]
    else:
        result["stdout"] = "VPN connection failed.\n" + result["stderr"]

    return _make_result(result["stdout"], vpn_status=True)


async def _cmd_vpn_status(args: Dict[str, Any]) -> Dict[str, Any]:
    """Check VPN connection status."""
    # Check for tun0 interface
    result = await _run_command(["ip", "addr", "show", _session["vpn_interface"]], timeout_ms=5000)

    if result["exit_code"] == 0 and _session["vpn_interface"] in result["stdout"]:
        _session["vpn_connected"] = True
        # Extract IP
        ip_match = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", result["stdout"])
        ip = ip_match.group(1) if ip_match else "unknown"
        return _make_result(f"VPN Connected. Interface: {_session['vpn_interface']}, IP: {ip}", vpn_status=True)

    _session["vpn_connected"] = False
    return _make_result("VPN not connected.", vpn_status=True)


async def _cmd_vpn_disconnect(args: Dict[str, Any]) -> Dict[str, Any]:
    """Disconnect from TryHackMe VPN."""
    result = await _run_command(["pkill", "-f", "openvpn"], timeout_ms=5000)
    _session["vpn_connected"] = False
    return _make_result("VPN disconnected.\n" + result["stdout"], vpn_status=True)


async def _cmd_nmap_scan(args: Dict[str, Any]) -> Dict[str, Any]:
    """Run nmap scan on target."""
    command = args.get("command", "")
    target_ip = args.get("target_ip", "")

    # Parse: nmap_scan <target_ip> [options]
    parts = command.split(None, 2)
    if not target_ip and len(parts) >= 2:
        target_ip = parts[1]

    if not target_ip:
        return _make_result("No target IP specified. Usage: nmap_scan <target_ip> [options]", is_error=True)

    _session["current_target"] = target_ip

    extra_opts = args.get("options", "")
    if len(parts) >= 3:
        extra_opts = parts[2]

    nmap_args = ["nmap", "-sV", "-sC", "-T4"]
    if extra_opts:
        nmap_args.extend(extra_opts.split())
    nmap_args.append(target_ip)

    result = await _run_command(nmap_args, timeout_ms=args.get("timeout", 120000))
    return _make_result(result["stdout"] or result["stderr"])


async def _cmd_gobuster(args: Dict[str, Any]) -> Dict[str, Any]:
    """Directory enumeration with gobuster."""
    command = args.get("command", "")
    target_url = args.get("target_url", "")

    parts = command.split(None, 3)
    if not target_url and len(parts) >= 2:
        target_url = parts[1]

    if not target_url:
        return _make_result("No target URL specified. Usage: gobuster <target_url> [wordlist]", is_error=True)

    wordlist = args.get("wordlist")
    if not wordlist and len(parts) >= 3:
        wordlist = parts[2]
    wordlist = _find_wordlist(wordlist)
    if not wordlist:
        return _make_result("No wordlist found. Install wordlists or specify path.", is_error=True)

    gobuster_args = ["gobuster", "dir", "-u", target_url, "-w", wordlist, "-q"]
    extra_opts = args.get("options", "")
    if extra_opts:
        gobuster_args.extend(extra_opts.split())

    result = await _run_command(gobuster_args, timeout_ms=args.get("timeout", 120000))
    return _make_result(result["stdout"] or result["stderr"])


async def _cmd_nikto_scan(args: Dict[str, Any]) -> Dict[str, Any]:
    """Web server vulnerability scan with nikto."""
    command = args.get("command", "")
    target_url = args.get("target_url", "")

    parts = command.split(None, 2)
    if not target_url and len(parts) >= 2:
        target_url = parts[1]

    if not target_url:
        return _make_result("No target URL specified. Usage: nikto_scan <target_url>", is_error=True)

    nikto_args = ["nikto", "-h", target_url]
    extra_opts = args.get("options", "")
    if extra_opts:
        nikto_args.extend(extra_opts.split())

    result = await _run_command(nikto_args, timeout_ms=args.get("timeout", 180000))
    return _make_result(result["stdout"] or result["stderr"])


async def _cmd_hydra_brute(args: Dict[str, Any]) -> Dict[str, Any]:
    """Brute force with hydra."""
    command = args.get("command", "")
    parts = command.split(None, 5)

    if len(parts) < 5:
        return _make_result(
            "Usage: hydra_brute <service> <target> <username> <wordlist>\n"
            "Example: hydra_brute ssh 10.10.10.5 admin /usr/share/wordlists/rockyou.txt",
            is_error=True,
        )

    service = parts[1]
    target = parts[2]
    username = parts[3]
    wordlist = parts[4] if len(parts) > 4 else args.get("wordlist", "")
    wordlist = _find_wordlist(wordlist)
    if not wordlist:
        return _make_result("No wordlist found.", is_error=True)

    hydra_args = ["hydra", "-l", username, "-P", wordlist, f"{service}://{target}"]
    extra_opts = args.get("options", "")
    if extra_opts:
        hydra_args.extend(extra_opts.split())

    result = await _run_command(hydra_args, timeout_ms=args.get("timeout", 300000))
    return _make_result(result["stdout"] or result["stderr"])


async def _cmd_enum4linux(args: Dict[str, Any]) -> Dict[str, Any]:
    """SMB enumeration with enum4linux."""
    command = args.get("command", "")
    target_ip = args.get("target_ip", "")

    parts = command.split(None, 2)
    if not target_ip and len(parts) >= 2:
        target_ip = parts[1]

    if not target_ip:
        return _make_result("No target IP specified. Usage: enum4linux <target_ip>", is_error=True)

    _session["current_target"] = target_ip
    result = await _run_command(["enum4linux", "-a", target_ip], timeout_ms=args.get("timeout", 120000))
    return _make_result(result["stdout"] or result["stderr"])


async def _cmd_smb_client(args: Dict[str, Any]) -> Dict[str, Any]:
    """SMB client operations."""
    command = args.get("command", "")
    target_ip = args.get("target_ip", "")

    parts = command.split(None, 3)
    if not target_ip and len(parts) >= 2:
        target_ip = parts[1]

    if not target_ip:
        return _make_result("No target IP specified. Usage: smb_client <target_ip> [share]", is_error=True)

    share = parts[2] if len(parts) > 2 else ""

    if share:
        smb_args = ["smbclient", f"//{target_ip}/{share}", "-N"]
    else:
        smb_args = ["smbclient", "-L", f"//{target_ip}", "-N"]

    result = await _run_command(smb_args, timeout_ms=args.get("timeout", 30000))
    return _make_result(result["stdout"] or result["stderr"])


async def _cmd_sqlmap(args: Dict[str, Any]) -> Dict[str, Any]:
    """SQL injection testing with sqlmap."""
    command = args.get("command", "")
    target_url = args.get("target_url", "")

    parts = command.split(None, 2)
    if not target_url and len(parts) >= 2:
        target_url = parts[1]

    if not target_url:
        return _make_result("No target URL specified. Usage: sqlmap <target_url>", is_error=True)

    sqlmap_args = ["sqlmap", "-u", target_url, "--batch", "--random-agent"]
    extra_opts = args.get("options", "")
    if extra_opts:
        sqlmap_args.extend(extra_opts.split())

    result = await _run_command(sqlmap_args, timeout_ms=args.get("timeout", 300000))
    return _make_result(result["stdout"] or result["stderr"])


async def _cmd_john_crack(args: Dict[str, Any]) -> Dict[str, Any]:
    """Crack hashes with John the Ripper."""
    command = args.get("command", "")
    parts = command.split(None, 3)

    if len(parts) < 2:
        return _make_result("Usage: john_crack <hash_file> [wordlist]", is_error=True)

    hash_file = parts[1]
    if not os.path.exists(hash_file):
        return _make_result(f"Hash file not found: {hash_file}", is_error=True)

    wordlist = parts[2] if len(parts) > 2 else args.get("wordlist", "")
    wordlist = _find_wordlist(wordlist)

    john_args = ["john", hash_file]
    if wordlist:
        john_args.extend(["--wordlist=" + wordlist])

    result = await _run_command(john_args, timeout_ms=args.get("timeout", 300000))

    # Show cracked passwords
    if result["exit_code"] == 0:
        show_result = await _run_command(["john", "--show", hash_file], timeout_ms=5000)
        result["stdout"] += "\n--- Cracked ---\n" + show_result["stdout"]

    return _make_result(result["stdout"] or result["stderr"])


async def _cmd_linpeas_upload(args: Dict[str, Any]) -> Dict[str, Any]:
    """Upload and run linpeas on target (requires SSH access)."""
    command = args.get("command", "")
    target_ip = args.get("target_ip", "")
    username = args.get("username", "")

    parts = command.split(None, 3)
    if not target_ip and len(parts) >= 2:
        target_ip = parts[1]
    if not username and len(parts) >= 3:
        username = parts[2]

    if not target_ip:
        return _make_result("No target IP specified. Usage: linpeas_upload <target_ip> [username]", is_error=True)

    username = username or "root"

    # Check if linpeas.sh exists locally
    linpeas_paths = [
        "./linpeas.sh",
        "/opt/linpeas/linpeas.sh",
        os.path.expanduser("~/tools/linpeas.sh"),
        os.path.expanduser("~/linpeas.sh"),
    ]
    linpeas_path = None
    for p in linpeas_paths:
        if os.path.exists(p):
            linpeas_path = p
            break

    if not linpeas_path:
        return _make_result(
            "linpeas.sh not found locally. Download it from:\n"
            "https://github.com/peass-ng/PEASS-ng/releases/latest/download/linpeas.sh\n"
            "Then place it in the current directory or ~/tools/.",
            is_error=True,
        )

    # Upload and run
    scp_result = await _run_command(
        ["scp", linpeas_path, f"{username}@{target_ip}:/tmp/linpeas.sh"],
        timeout_ms=30000,
    )
    if scp_result["exit_code"] != 0:
        return _make_result(f"Failed to upload linpeas: {scp_result['stderr']}", is_error=True)

    ssh_result = await _run_command(
        ["ssh", f"{username}@{target_ip}", "chmod +x /tmp/linpeas.sh && /tmp/linpeas.sh"],
        timeout_ms=args.get("timeout", 120000),
    )

    return _make_result(ssh_result["stdout"] or ssh_result["stderr"])


async def _cmd_submit_flag(args: Dict[str, Any]) -> Dict[str, Any]:
    """Record a captured flag."""
    command = args.get("command", "")
    flag = command.replace("submit_flag ", "", 1).strip()

    if not flag:
        return _make_result("No flag provided. Usage: submit_flag <flag_value>", is_error=True)

    # Common CTF flag patterns
    flag_patterns = [
        r"THM\{[^}]+\}",
        r"flag\{[^}]+\}",
        r"CTF\{[^}]+\}",
        r"HTB\{[^}]+\}",
        r"[A-Za-z0-9+/=]{20,}",
    ]

    is_valid = any(re.match(p, flag) for p in flag_patterns)

    if flag not in _session["flags_found"]:
        _session["flags_found"].append(flag)

    return _make_result(
        f"Flag recorded: {flag}\n"
        + ("Format looks valid! " if is_valid else "Flag format may be unusual. ")
        + f"Total flags found: {len(_session['flags_found'])}",
        flags=True,
    )


async def _cmd_flags_found(args: Dict[str, Any]) -> Dict[str, Any]:
    """List all flags found this session."""
    if not _session["flags_found"]:
        return _make_result("No flags found yet. Keep enumerating!", flags=True)

    result = f"Flags found ({len(_session['flags_found'])}):\n"
    for i, flag in enumerate(_session["flags_found"], 1):
        result += f"  {i}. {flag}\n"
    return _make_result(result, flags=True)


async def _cmd_room_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get info about a TryHackMe room."""
    command = args.get("command", "")
    room_name = command.replace("room_info ", "", 1).strip()

    if not room_name:
        return _make_result("No room name specified. Usage: room_info <room_name>", is_error=True)

    _session["current_room"] = room_name

    # Try to fetch room page
    result = await _run_command(
        ["curl", "-s", "-L", f"https://tryhackme.com/room/{room_name}"],
        timeout_ms=15000,
    )

    if result["exit_code"] == 0 and result["stdout"]:
        # Extract title
        title_match = re.search(r"<title>(.*?)</title>", result["stdout"], re.IGNORECASE)
        title = title_match.group(1) if title_match else room_name

        # Extract description
        desc_match = re.search(
            r'<meta\s+name="description"\s+content="([^"]+)"',
            result["stdout"], re.IGNORECASE,
        )
        description = desc_match.group(1) if desc_match else "No description found."

        # Check if free room
        is_free = "free" in result["stdout"].lower()

        info = (
            f"Room: {title}\n"
            f"URL: https://tryhackme.com/room/{room_name}\n"
            f"Free Room: {'Yes' if is_free else 'Unknown (check site)'}\n"
            f"Description: {description}\n"
        )
        return _make_result(info)

    return _make_result(f"Could not fetch room info for '{room_name}'. Check the room name.", is_error=True)


async def _cmd_check_tools(args: Dict[str, Any]) -> Dict[str, Any]:
    """Check which CTF tools are available."""
    available = []
    missing = []

    for name, cmd in _CTF_TOOLS.items():
        result = await _run_command(["which", cmd], timeout_ms=3000)
        if result["exit_code"] == 0 and result["stdout"].strip():
            available.append(f"  ✅ {name}: {result['stdout'].strip()}")
        else:
            missing.append(f"  ❌ {name} ({cmd})")

    output = "=== Available CTF Tools ===\n" + "\n".join(available)
    if missing:
        output += "\n\n=== Missing Tools ===\n" + "\n".join(missing)
        output += "\n\nInstall missing tools with: sudo apt install <package>"

    return _make_result(output)


async def _cmd_start_machine(args: Dict[str, Any]) -> Dict[str, Any]:
    """Note about starting a TryHackMe machine."""
    command = args.get("command", "")
    target_ip = args.get("target_ip", "")

    parts = command.split(None, 2)
    if not target_ip and len(parts) >= 2:
        target_ip = parts[1]

    if not target_ip:
        return _make_result(
            "To start a TryHackMe machine:\n"
            "1. Go to https://tryhackme.com/ and start the machine in your browser\n"
            "2. Once you have the target IP, use: nmap_scan <target_ip>\n"
            "3. Make sure your VPN is connected: vpn_status",
            is_error=True,
        )

    _session["current_target"] = target_ip
    return _make_result(
        f"Target set to {target_ip}.\n"
        "Make sure the machine is running on TryHackMe and your VPN is connected.\n"
        "Start enumeration with: nmap_scan {target_ip}"
    )


# ── Helpers ─────────────────────────────────────────────────────────────────

def _make_result(
    message: str,
    is_error: bool = False,
    vpn_status: bool = False,
    flags: bool = False,
) -> Dict[str, Any]:
    return {
        "stdout": message if not is_error else "",
        "stderr": message if is_error else "",
        "exit_code": 1 if is_error else 0,
        "flags_found": _session["flags_found"] if flags else [],
        "vpn_connected": _session["vpn_connected"] if vpn_status else None,
        "interrupted": False,
    }


# ── Command dispatch ────────────────────────────────────────────────────────

_COMMAND_MAP = {
    "vpn_connect": _cmd_vpn_connect,
    "vpn_status": _cmd_vpn_status,
    "vpn_disconnect": _cmd_vpn_disconnect,
    "start_machine": _cmd_start_machine,
    "nmap_scan": _cmd_nmap_scan,
    "gobuster": _cmd_gobuster,
    "nikto_scan": _cmd_nikto_scan,
    "hydra_brute": _cmd_hydra_brute,
    "enum4linux": _cmd_enum4linux,
    "smb_client": _cmd_smb_client,
    "sqlmap": _cmd_sqlmap,
    "john_crack": _cmd_john_crack,
    "linpeas_upload": _cmd_linpeas_upload,
    "submit_flag": _cmd_submit_flag,
    "flags_found": _cmd_flags_found,
    "room_info": _cmd_room_info,
    "check_tools": _cmd_check_tools,
}


async def call(args: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
    """Main entry point for the TryHackMe tool."""
    command = (args.get("command") or "").strip()

    if not command:
        return _make_result(
            "No command specified. Available commands:\n"
            + "\n".join(f"  - {cmd}" for cmd in sorted(_COMMAND_MAP)),
            is_error=True,
        )

    parts = command.split(None, 1)
    sub_cmd = parts[0].lower()

    handler = _COMMAND_MAP.get(sub_cmd)
    if handler:
        return await handler(args)

    return _make_result(
        f"Unknown command: '{sub_cmd}'. Available: {', '.join(sorted(_COMMAND_MAP))}",
        is_error=True,
    )


async def description() -> str:
    return "Interact with TryHackMe CTF platform — VPN, scanning, enumeration, and flag tracking."


async def prompt() -> str:
    return (
        "Use this tool for TryHackMe CTF competitions and penetration testing practice. "
        "First connect to TryHackMe VPN with 'vpn_connect <config_path>', then start "
        "enumerating targets. Typical workflow:\n"
        "1. vpn_connect — Connect to TryHackMe network\n"
        "2. nmap_scan <target_ip> — Discover open ports and services\n"
        "3. gobuster <target_url> — Find hidden directories\n"
        "4. enum4linux <target_ip> — Enumerate SMB shares (Windows targets)\n"
        "5. nikto_scan <target_url> — Scan for web vulnerabilities\n"
        "6. hydra_brute — Brute force credentials if needed\n"
        "7. submit_flag <flag> — Record captured flags\n"
        "Use 'check_tools' to see which CTF tools are available locally."
    )


def userFacingName() -> str:
    return "TryHackMe"


def getToolUseSummary(input_data: Dict[str, Any]) -> str:
    cmd = input_data.get("command", "")
    if cmd.startswith("nmap_scan"):
        return f"THM nmap: {input_data.get('target_ip', '') or cmd[10:50]}"
    if cmd.startswith("submit_flag"):
        return "THM: Flag submitted!"
    if cmd.startswith("vpn_"):
        return f"THM VPN: {cmd}"
    return f"THM: {cmd[:60]}"

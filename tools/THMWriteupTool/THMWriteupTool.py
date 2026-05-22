"""
THMWriteupTool — TryHackMe Write-up Database & Auto-Exploit Engine.

Searches GitHub and the web for CTF write-ups, builds a local knowledge
database, fingerprints target machines to identify the room, and auto-exploits
based on known solutions. Optimized for King of the Hill speed runs.

Capabilities:
- GitHub write-up search & ingestion (THM room write-ups)
- Web scraping of CTF write-up sites (medium, dev.to, personal blogs)
- Local write-up database with room fingerprinting
- Target fingerprinting: identify which THM room a target IP belongs to
- Auto-exploit: follow write-up steps automatically for fastest KOTH capture
- KOTH speed-run mode: pre-load known exploits, skip recon, go straight to flags
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TOOL_NAME = "THMWriteup"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["command"],
    "properties": {
        "command": {
            "type": "string",
            "description": (
                "The THM write-up operation. One of:\n"
                "- 'search <room_name>' — Search GitHub + web for write-ups on a THM room\n"
                "- 'ingest <url>' — Fetch and parse a specific write-up URL into the DB\n"
                "- 'ingest_github <room_name>' — Auto-search GitHub and ingest top write-ups\n"
                "- 'fingerprint <target_ip>' — Fingerprint target to identify which THM room it is\n"
                "- 'auto_exploit <target_ip>' — Auto-exploit using known write-up steps\n"
                "- 'kotb_speedrun <target_ip>' — KOTH speed-run: pre-load exploits, skip recon\n"
                "- 'db_list' — List all rooms in the local write-up database\n"
                "- 'db_search <keyword>' — Search the local write-up database\n"
                "- 'db_show <room_name>' — Show full write-up for a room from the DB\n"
                "- 'db_stats' — Show database statistics\n"
                "- 'db_export <path>' — Export the write-up database to JSON\n"
                "- 'db_import <path>' — Import a write-up database from JSON\n"
                "- 'build_index' — Rebuild the room fingerprint index\n"
                "- 'check_tools' — Check which tools are available for auto-exploit"
            ),
        },
        "target_ip": {
            "type": "string",
            "description": "Target IP address for fingerprinting or exploitation.",
        },
        "room_name": {
            "type": "string",
            "description": "TryHackMe room name to search for.",
        },
        "url": {
            "type": "string",
            "description": "URL of a write-up to ingest.",
        },
        "keyword": {
            "type": "string",
            "description": "Keyword to search the local database.",
        },
        "path": {
            "type": "string",
            "description": "File path for import/export.",
        },
        "timeout": {
            "type": "number",
            "description": "Operation timeout in milliseconds (default: 300000).",
            "default": 300000,
        },
        "description": {
            "type": "string",
            "description": "Description of what this operation does.",
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "result": {"type": "string"},
        "room_identified": {"type": "string"},
        "confidence": {"type": "number"},
        "writeup_count": {"type": "integer"},
        "steps_executed": {"type": "integer"},
        "flags_captured": {"type": "array", "items": {"type": "string"}},
        "db_size": {"type": "integer"},
        "summary": {"type": "string"},
        "interrupted": {"type": "boolean"},
    },
}

# ── Database path ────────────────────────────────────────────────────────────
_DB_DIR = Path.home() / ".vivian" / "thm_writeups"
_DB_FILE = _DB_DIR / "writeup_db.json"
_INDEX_FILE = _DB_DIR / "fingerprint_index.json"

# ── Session state ────────────────────────────────────────────────────────────
_session: Dict[str, Any] = {
    "target": None,
    "room_identified": None,
    "flags_captured": [],
    "steps_executed": 0,
    "current_phase": "idle",
}

# ── Known THM room fingerprints ──────────────────────────────────────────────
# Format: (room_name, fingerprint_patterns, common_ports, key_services, difficulty)
_ROOM_FINGERPRINTS: List[Tuple[str, List[str], List[int], List[str], str]] = [
    # Easy rooms
    ("simple_ctf", ["simple ctf", "cms made simple"], [21, 80, 2222], ["ftp", "http", "ssh"], "easy"),
    ("pickle_rick", ["pickle rick", "rick and morty"], [22, 80], ["ssh", "http"], "easy"),
    ("basic_pentesting", ["basic pentest", "basic pentesting"], [21, 22, 80, 8080], ["ftp", "ssh", "http"], "easy"),
    ("vulnversity", ["vulnversity", "vuln university"], [21, 22, 139, 445, 3128, 3333], ["ftp", "ssh", "smb", "squid", "http"], "easy"),
    ("blue", ["blue", "ms17-010", "eternalblue"], [135, 139, 445], ["msrpc", "netbios", "smb"], "easy"),
    ("ignite", ["ignite", "fuel cms"], [80], ["http"], "easy"),
    ("kenobi", ["kenobi", "star wars", "nfs"], [21, 22, 111, 139, 445, 2049], ["ftp", "ssh", "rpcbind", "smb", "nfs"], "easy"),
    ("steel_mountain", ["steel mountain", "http file server"], [80, 8080, 5985], ["http", "winrm"], "easy"),
    ("alfred", ["alfred", "jenkins"], [80, 8080, 3389], ["http", "rdp"], "easy"),
    ("hack_park", ["hack park", "blogengine"], [80, 3389], ["http", "rdp"], "easy"),
    ("skynet", ["skynet", "terminator", "squirrelmail"], [22, 80, 110, 139, 143, 445], ["ssh", "http", "pop3", "smb", "imap"], "easy"),
    ("daily_bugle", ["daily bugle", "joomla"], [22, 80, 3306], ["ssh", "http", "mysql"], "medium"),
    ("overpass", ["overpass", "overpass go"], [22, 80], ["ssh", "http"], "easy"),
    ("lazy_admin", ["lazy admin", "sweetrice"], [22, 80], ["ssh", "http"], "easy"),
    ("bounty_hacker", ["bounty hacker", "cowboy bebop"], [21, 22, 80], ["ftp", "ssh", "http"], "easy"),
    ("agent_sudo", ["agent sudo", "sudo"], [21, 22, 80], ["ftp", "ssh", "http"], "easy"),
    ("mr_robot", ["mr robot", "wordpress"], [22, 80, 443], ["ssh", "http", "https"], "medium"),
    ("thompson", ["thompson", "tomcat"], [22, 8009, 8080], ["ssh", "ajp", "http"], "easy"),
    ("ice", ["ice", "icecast"], [135, 139, 445, 8000], ["msrpc", "netbios", "smb", "icecast"], "easy"),
    ("blaster", ["blaster", "iis"], [80, 3389], ["http", "rdp"], "easy"),
    ("relevant", ["relevant", "iis", "smb"], [80, 135, 139, 445, 3389], ["http", "msrpc", "smb", "rdp"], "medium"),
    ("internal", ["internal", "wordpress", "phpmyadmin"], [22, 80], ["ssh", "http"], "hard"),
    ("game_zone", ["game zone", "sql injection"], [22, 80], ["ssh", "http"], "medium"),
    ("startup", ["startup", "ftp anonymous"], [21, 22, 80], ["ftp", "ssh", "http"], "easy"),
    ("chill_hack", ["chill hack", "command injection"], [21, 22, 80], ["ftp", "ssh", "http"], "easy"),
    ("c4ptur3_th3_fl4g", ["capture the flag", "rot13", "base64"], [21, 22, 80], ["ftp", "ssh", "http"], "easy"),
    ("brooklyn_nine_nine", ["brooklyn nine nine", "steganography"], [21, 22, 80], ["ftp", "ssh", "http"], "easy"),
    ("tomghost", ["tom ghost", "tomcat ghostcat"], [22, 8009, 8080], ["ssh", "ajp", "http"], "easy"),
    ("wgel", ["wgel", "ssh private key"], [22, 80], ["ssh", "http"], "easy"),
    ("goldeneye", ["goldeneye", "james bond", "pop3"], [25, 80, 110, 55006, 55007], ["smtp", "http", "pop3"], "medium"),
    ("hacktivitycon_ctf", ["hacktivitycon", "ctf"], [22, 80], ["ssh", "http"], "easy"),
    ("mustacchio", ["mustacchio", "xxe"], [22, 80, 8765], ["ssh", "http"], "easy"),
    ("oh_my_webserver", ["oh my webserver", "apache"], [22, 80], ["ssh", "http"], "medium"),
    ("colddbox", ["colddbox", "wordpress"], [22, 80, 4512], ["ssh", "http"], "easy"),
    ("cyborg", ["cyborg", "borg backup"], [22, 80], ["ssh", "http"], "easy"),
    ("archangel", ["archangel", "lfi"], [22, 80], ["ssh", "http"], "easy"),
    ("all_in_one", ["all in one", "wordpress"], [21, 22, 80], ["ftp", "ssh", "http"], "easy"),
    ("bolt", ["bolt cms", "bolt"], [22, 80, 8000], ["ssh", "http"], "easy"),
    ("year_of_the_rabbit", ["year of the rabbit", "ftp"], [21, 22, 80], ["ftp", "ssh", "http"], "easy"),
    ("jack_of_all_trades", ["jack of all trades", "stego"], [22, 80], ["ssh", "http"], "easy"),
    ("overpass2_hacked", ["overpass2", "pcap"], [22, 80, 2222], ["ssh", "http"], "easy"),
    ("gaming_server", ["gaming server", "lxd"], [22, 80], ["ssh", "http"], "easy"),
    ("hacker_vs_hacker", ["hacker vs hacker", "reverse shell"], [22, 80], ["ssh", "http"], "easy"),
    ("undiscovered", ["undiscovered", "smb"], [22, 80, 139, 445], ["ssh", "http", "smb"], "medium"),
    ("razor_black", ["razor black", "active directory"], [53, 88, 111, 139, 389, 445, 2049], ["dns", "kerberos", "ldap", "smb", "nfs"], "medium"),
    ("watcher", ["watcher", "lfi"], [21, 22, 80], ["ftp", "ssh", "http"], "medium"),
    ("dogcat", ["dogcat", "lfi", "docker"], [22, 80], ["ssh", "http"], "medium"),
    ("jpggat", ["jpggat", "polyglot"], [22, 80], ["ssh", "http"], "medium"),
    ("madeyes_castle", ["madeyes castle", "sql injection"], [22, 80], ["ssh", "http"], "medium"),
    ("anonymous", ["anonymous", "ftp anonymous"], [21, 22, 139, 445], ["ftp", "ssh", "smb"], "medium"),
    ("brainpan", ["brainpan", "buffer overflow"], [9999, 10000], ["brainpan", "http"], "medium"),
    ("gatekeeper", ["gatekeeper", "buffer overflow"], [135, 139, 445, 31337], ["smb", "gatekeeper"], "medium"),
    ("buffer_overflow_prep", ["buffer overflow prep", "oscp"], [1337], ["oscp"], "medium"),
    ("chronicle", ["chronicle", "git"], [22, 80, 8081], ["ssh", "http"], "medium"),
    ("glitch", ["glitch", "nodejs"], [80], ["http"], "easy"),
    ("convert_my_video", ["convert my video", "ffmpeg"], [22, 80], ["ssh", "http"], "medium"),
    ("harder", ["harder", "php"], [22, 80], ["ssh", "http"], "medium"),
    ("ultratech", ["ultratech", "api"], [22, 8081, 31331], ["ssh", "http", "api"], "medium"),
    ("blueprint", ["blueprint", "windows"], [80, 135, 139, 443, 445, 3306, 8080], ["http", "smb", "mysql"], "easy"),
    ("retro", ["retro", "windows"], [80, 3389, 5985], ["http", "rdp", "winrm"], "medium"),
    ("anthem", ["anthem", "windows", "iis"], [80, 3389], ["http", "rdp"], "easy"),
    ("blog", ["blog", "wordpress"], [22, 80, 139, 445], ["ssh", "http", "smb"], "medium"),
    ("wonderland", ["wonderland", "alice in wonderland"], [22, 80], ["ssh", "http"], "medium"),
    ("rootme", ["rootme", "php"], [22, 80], ["ssh", "http"], "easy"),
    ("attacktive_directory", ["attacktive directory", "active directory"], [53, 80, 88, 135, 139, 389, 445, 464, 593, 636, 3268, 3269, 3389, 5985, 9389], ["dns", "http", "kerberos", "ldap", "smb", "rdp", "winrm"], "medium"),
    ("enterprise", ["enterprise", "wordpress"], [22, 80, 443, 8080], ["ssh", "http", "https"], "medium"),
    ("the_server_from_hell", ["server from hell", "nfs"], [22, 111, 2049, 12345], ["ssh", "rpcbind", "nfs"], "medium"),
    ("koth_food_ctf", ["koth food", "king of the hill"], [22, 80, 3306, 9999], ["ssh", "http", "mysql"], "hard"),
    ("koth_hackers", ["koth hackers", "king of the hill"], [22, 80, 445, 3306], ["ssh", "http", "smb", "mysql"], "hard"),
    ("koth_bank", ["koth bank", "king of the hill"], [22, 80, 443, 3306], ["ssh", "http", "https", "mysql"], "hard"),
    ("koth_battlegrounds", ["koth battlegrounds", "king of the hill"], [22, 80, 445], ["ssh", "http", "smb"], "hard"),
]

# ── Common KOTH exploit steps (pre-loaded for speed) ────────────────────────
_KOTH_QUICK_STEPS: Dict[str, List[str]] = {
    "default": [
        "# KOTH Speed Run — Default Playbook",
        "1. SSH brute force with common creds (root:password, root:toor, admin:admin)",
        "2. Upload SSH key for persistence",
        "3. Change all user passwords",
        "4. Remove other users' SSH keys from authorized_keys",
        "5. Set up iptables to block competitors",
        "6. Find and secure SUID binaries",
        "7. Set up cron job for persistence",
        "8. Start mining or scoring service",
        "9. Monitor /tmp for competitor activity",
        "10. Lock down writable directories",
    ],
    "web": [
        "# KOTH Speed Run — Web Server Focus",
        "1. Check for default credentials on web apps (admin:admin, admin:password)",
        "2. Upload web shell via vulnerable upload form",
        "3. Get reverse shell from web shell",
        "4. Upgrade to full TTY",
        "5. Add SSH key for persistence",
        "6. Kill competitor shells (ps aux | grep sh | awk '{print $2}' | xargs kill -9)",
        "7. Set up iptables rules",
        "8. Change all passwords",
        "9. Remove competitor SSH keys",
        "10. Start scoring service",
    ],
    "smb": [
        "# KOTH Speed Run — SMB Focus",
        "1. Check for anonymous SMB login",
        "2. Enumerate shares with smbclient",
        "3. Download any accessible files",
        "4. Check for writable shares",
        "5. Upload reverse shell via writable share",
        "6. Execute via scheduled task or service",
        "7. Get shell, add persistence",
        "8. Lock down SMB shares",
        "9. Change passwords",
        "10. Block competitors",
    ],
}


# ── Helper: load/save database ───────────────────────────────────────────────

def _load_db() -> Dict[str, Any]:
    """Load the write-up database from disk."""
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    if _DB_FILE.exists():
        try:
            return json.loads(_DB_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {"rooms": {}, "writeups": [], "last_updated": None}
    return {"rooms": {}, "writeups": [], "last_updated": None}


def _save_db(db: Dict[str, Any]) -> None:
    """Save the write-up database to disk."""
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    db["last_updated"] = time.time()
    _DB_FILE.write_text(json.dumps(db, indent=2))


def _load_index() -> Dict[str, Any]:
    """Load the fingerprint index."""
    if _INDEX_FILE.exists():
        try:
            return json.loads(_INDEX_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_index(index: Dict[str, Any]) -> None:
    """Save the fingerprint index."""
    _INDEX_FILE.write_text(json.dumps(index, indent=2))


# ── Helper: run shell command ────────────────────────────────────────────────

async def _run_cmd(cmd: str, timeout: int = 60) -> Tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        return proc.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")
    except asyncio.TimeoutError:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


# ── Helper: check if a tool is available ─────────────────────────────────────

def _has_tool(name: str) -> bool:
    """Check if a command-line tool is available."""
    try:
        result = subprocess.run(
            ["which", name] if os.name != "nt" else ["where", name],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


# ── Helper: fetch URL ────────────────────────────────────────────────────────

def _fetch_url(url: str, timeout: int = 30) -> Optional[str]:
    """Fetch content from a URL."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode(errors="replace")
    except Exception:
        return None


# ── GitHub search ────────────────────────────────────────────────────────────

def _search_github(room_name: str) -> List[Dict[str, str]]:
    """Search GitHub for THM write-ups on a specific room."""
    results: List[Dict[str, str]] = []
    query = urllib.parse.quote(f"TryHackMe {room_name} writeup")
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&per_page=10"

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "VivianCLI-THMWriteup",
                "Accept": "application/vnd.github.v3+json",
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            for item in data.get("items", []):
                results.append({
                    "name": item.get("full_name", ""),
                    "url": item.get("html_url", ""),
                    "description": item.get("description", ""),
                    "stars": item.get("stargazers_count", 0),
                    "updated": item.get("updated_at", ""),
                })
    except Exception:
        pass

    return results


def _search_github_code(room_name: str) -> List[Dict[str, str]]:
    """Search GitHub code for THM write-up markdown files."""
    results: List[Dict[str, str]] = []
    query = urllib.parse.quote(f"TryHackMe {room_name} flag user.txt root.txt")
    url = f"https://api.github.com/search/code?q={query}&per_page=10"

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "VivianCLI-THMWriteup",
                "Accept": "application/vnd.github.v3+json",
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            for item in data.get("items", []):
                results.append({
                    "name": item.get("repository", {}).get("full_name", ""),
                    "path": item.get("path", ""),
                    "url": item.get("html_url", ""),
                })
    except Exception:
        pass

    return results


# ── Web search for write-ups ─────────────────────────────────────────────────

_WRITEUP_SITES = [
    "medium.com",
    "dev.to",
    "infosecwriteups.com",
    "hackmd.io",
    "0xdf.gitlab.io",
    "juggernaut-sec.com",
    "hackthebox.writeup.rip",
    "cybersecnerds.com",
    "tryhackme.com/resources",
]


def _search_web_writeups(room_name: str) -> List[Dict[str, str]]:
    """Search the web for THM write-ups using DuckDuckGo or Google."""
    results: List[Dict[str, str]] = []
    query = urllib.parse.quote(f"TryHackMe {room_name} writeup walkthrough")

    # Try DuckDuckGo HTML search (no API key needed)
    ddg_url = f"https://html.duckduckgo.com/html/?q={query}"
    html = _fetch_url(ddg_url, timeout=15)
    if html:
        # Extract result links
        link_pattern = re.compile(
            r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
            re.IGNORECASE
        )
        for match in link_pattern.finditer(html):
            url = match.group(1)
            title = match.group(2).strip()
            # Filter to known write-up sites
            if any(site in url for site in _WRITEUP_SITES):
                results.append({"title": title, "url": url, "source": "web"})

    return results[:15]


# ── Write-up parsing ─────────────────────────────────────────────────────────

def _parse_writeup(content: str, url: str) -> Dict[str, Any]:
    """Parse a write-up page to extract structured information."""
    parsed: Dict[str, Any] = {
        "url": url,
        "room_name": "",
        "flags": [],
        "steps": [],
        "tools_used": [],
        "ports": [],
        "services": [],
        "vulnerabilities": [],
        "privesc_method": "",
        "raw_length": len(content),
    }

    # Try to extract room name
    room_patterns = [
        r'(?:THM|TryHackMe)\s*(?:Room|Box)?\s*[:>-]?\s*([A-Za-z0-9_ -]+?)(?:\s*(?:Write-?up|Walkthrough|CTF|Room))',
        r'#+\s*(?:THM|TryHackMe)\s*[:>-]?\s*(.+)',
        r'(?:Room|Box)\s*Name\s*[:>-]?\s*(.+)',
    ]
    for pattern in room_patterns:
        m = re.search(pattern, content, re.IGNORECASE)
        if m:
            parsed["room_name"] = m.group(1).strip()
            break

    # Extract flags
    flag_patterns = [
        r'(?:flag|FLAG)\s*[:=]\s*(\{?[A-Za-z0-9_{}-]+\}?)',
        r'(?:user\.txt|root\.txt|flag\.txt)\s*[:>-]\s*(\S+)',
        r'THM\{[^}]+\}',
        r'flag\{[^}]+\}',
    ]
    seen_flags = set()
    for pattern in flag_patterns:
        for m in re.finditer(pattern, content):
            flag = m.group(0) if not m.groups() else m.group(1)
            if flag not in seen_flags and len(flag) > 3:
                seen_flags.add(flag)
                parsed["flags"].append(flag)

    # Extract steps (numbered lists)
    step_pattern = re.compile(r'^\s*(?:\d+[.)]\s*|[-*]\s*)(.+)$', re.MULTILINE)
    for m in step_pattern.finditer(content):
        step = m.group(1).strip()
        if len(step) > 10 and len(step) < 500:
            parsed["steps"].append(step)

    # Extract tools
    common_tools = [
        "nmap", "gobuster", "nikto", "hydra", "john", "hashcat",
        "metasploit", "msfconsole", "msfvenom", "sqlmap", "burp",
        "dirb", "dirbuster", "ffuf", "wfuzz", "enum4linux",
        "smbclient", "smbmap", "crackmapexec", "evil-winrm",
        "netcat", "nc", "python", "perl", "php", "bash",
        "linpeas", "winpeas", "psexec", "mimikatz", "responder",
        "chisel", "socat", "ssh", "ftp", "wget", "curl",
    ]
    content_lower = content.lower()
    for tool in common_tools:
        if tool in content_lower:
            parsed["tools_used"].append(tool)

    # Extract ports
    port_pattern = re.compile(r'(?:port|Port)\s*(\d+)\s*(?:[/-]\s*(?:tcp|udp))?\s*(?:open|Open)?\s*(?:[-:]\s*)?(\w+)')
    for m in port_pattern.finditer(content):
        port = int(m.group(1))
        service = m.group(2) if m.lastindex and m.lastindex >= 2 else ""
        if port not in [p for p, _ in parsed["ports"]]:
            parsed["ports"].append((port, service))

    # Extract vulnerabilities
    vuln_keywords = [
        "sql injection", "xss", "csrf", "ssrf", "lfi", "rfi",
        "command injection", "buffer overflow", "privilege escalation",
        "deserialization", "xxe", "idor", "path traversal",
        "file upload", "race condition", "misconfiguration",
        "default credentials", "weak password", "anonymous login",
        "remote code execution", "rce", "reverse shell",
    ]
    for vuln in vuln_keywords:
        if vuln in content_lower:
            parsed["vulnerabilities"].append(vuln)

    # Extract privesc method
    privesc_patterns = [
        r'(?:privilege escalation|privesc|Privilege Escalation)\s*[:>-]?\s*(.+?)(?:\n|$)',
        r'(?:sudo -l|SUID|suid)\s*(.+?)(?:\n|$)',
        r'(?:root|Root)\s*(?:flag|Flag)\s*[:>-]?\s*(.+?)(?:\n|$)',
    ]
    for pattern in privesc_patterns:
        m = re.search(pattern, content, re.IGNORECASE)
        if m:
            parsed["privesc_method"] = m.group(1).strip()[:200]
            break

    return parsed


# ── Fingerprinting ───────────────────────────────────────────────────────────

async def _fingerprint_target(target_ip: str) -> Dict[str, Any]:
    """Fingerprint a target to identify which THM room it is."""
    result: Dict[str, Any] = {
        "target": target_ip,
        "open_ports": [],
        "services": {},
        "room_candidates": [],
        "best_match": None,
        "confidence": 0.0,
    }

    # Quick port scan (top 1000)
    if _has_tool("nmap"):
        code, stdout, stderr = await _run_cmd(
            f"nmap -T4 --top-ports 1000 -sV {target_ip} 2>/dev/null",
            timeout=120
        )
        if code == 0:
            for line in stdout.splitlines():
                port_match = re.match(r'(\d+)/tcp\s+open\s+(\S+)\s*(.*)', line)
                if port_match:
                    port = int(port_match.group(1))
                    service = port_match.group(2)
                    version = port_match.group(3).strip()
                    result["open_ports"].append(port)
                    result["services"][port] = {"service": service, "version": version}

    # Match against known room fingerprints
    open_set = set(result["open_ports"])
    for room_name, patterns, ports, services, difficulty in _ROOM_FINGERPRINTS:
        port_overlap = len(open_set & set(ports))
        port_score = port_overlap / max(len(ports), 1)

        # Check service matches
        service_matches = 0
        for port in ports:
            if port in result["services"]:
                svc = result["services"][port]["service"].lower()
                for expected in services:
                    if expected in svc or svc in expected:
                        service_matches += 1
                        break

        service_score = service_matches / max(len(services), 1)
        total_score = (port_score * 0.6) + (service_score * 0.4)

        if total_score > 0.2:
            result["room_candidates"].append({
                "room_name": room_name,
                "score": round(total_score, 3),
                "difficulty": difficulty,
                "port_overlap": port_overlap,
                "service_matches": service_matches,
            })

    # Sort by score
    result["room_candidates"].sort(key=lambda x: x["score"], reverse=True)

    if result["room_candidates"]:
        best = result["room_candidates"][0]
        result["best_match"] = best["room_name"]
        result["confidence"] = best["score"]

    return result


# ── Auto-exploit ─────────────────────────────────────────────────────────────

async def _auto_exploit(target_ip: str, room_name: Optional[str] = None, speedrun: bool = False) -> Dict[str, Any]:
    """Auto-exploit a target based on write-up knowledge."""
    result: Dict[str, Any] = {
        "target": target_ip,
        "room_name": room_name,
        "flags_captured": [],
        "steps_executed": 0,
        "exploits_attempted": [],
        "successful_exploits": [],
        "summary": "",
    }

    db = _load_db()

    # If no room name, fingerprint first
    if not room_name:
        fp = await _fingerprint_target(target_ip)
        room_name = fp.get("best_match")
        result["room_name"] = room_name
        result["fingerprint"] = fp

    if not room_name:
        result["summary"] = "Could not identify the room. Run fingerprint first."
        return result

    # Look up write-up in database
    room_data = db.get("rooms", {}).get(room_name.lower().replace(" ", "_"), {})
    writeups = room_data.get("writeups", [])

    if not writeups and not speedrun:
        result["summary"] = f"No write-ups found for '{room_name}'. Run 'ingest_github {room_name}' first."
        return result

    # Build exploit plan from write-ups
    steps: List[str] = []

    if speedrun:
        # KOTH speed-run: use pre-loaded quick steps
        fp = result.get("fingerprint", {})
        services = set()
        for port_info in (fp.get("services") or {}).values():
            services.add(port_info.get("service", "").lower())

        if "http" in services or "https" in services:
            steps = _KOTH_QUICK_STEPS.get("web", _KOTH_QUICK_STEPS["default"])
        elif "smb" in services:
            steps = _KOTH_QUICK_STEPS.get("smb", _KOTH_QUICK_STEPS["default"])
        else:
            steps = _KOTH_QUICK_STEPS["default"]
    else:
        # Extract steps from write-ups
        for wu in writeups:
            for step in wu.get("steps", [])[:20]:
                if step not in steps:
                    steps.append(step)

    # Execute steps
    for step in steps:
        if step.startswith("#"):
            continue  # Skip comment/header lines

        result["steps_executed"] += 1

        # Try to execute the step as a command if it looks like one
        if any(cmd in step.lower() for cmd in ["nmap", "gobuster", "ssh", "ftp", "curl", "wget", "nc", "python", "php", "smbclient", "enum4linux", "hydra", "sqlmap", "john", "hashcat"]):
            result["exploits_attempted"].append(step[:100])
            # Replace placeholders
            cmd = step.replace("<target_ip>", target_ip).replace("<TARGET>", target_ip).replace("$IP", target_ip)
            code, stdout, stderr = await _run_cmd(cmd, timeout=30)
            if code == 0 and stdout:
                result["successful_exploits"].append(step[:100])
                # Check for flags in output
                for flag_pattern in [r'THM\{[^}]+\}', r'flag\{[^}]+\}', r'[A-Za-z0-9]{32}']:
                    for m in re.finditer(flag_pattern, stdout + stderr):
                        flag = m.group(0)
                        if flag not in result["flags_captured"]:
                            result["flags_captured"].append(flag)

    result["summary"] = (
        f"Auto-exploit complete for {room_name}. "
        f"Executed {result['steps_executed']} steps, "
        f"captured {len(result['flags_captured'])} flags."
    )

    return result


# ── Main call function ───────────────────────────────────────────────────────

async def call(args: Dict[str, Any], context: Optional[Any] = None) -> Dict[str, Any]:
    """Execute a THMWriteupTool command."""
    command = (args.get("command") or "").strip()
    target_ip = args.get("target_ip", "")
    room_name = args.get("room_name", "")
    url = args.get("url", "")
    keyword = args.get("keyword", "")
    path = args.get("path", "")
    timeout = int(args.get("timeout", 300000)) // 1000

    db = _load_db()

    # ── search ───────────────────────────────────────────────────────────
    if command.startswith("search "):
        query = command[7:].strip() or room_name
        if not query:
            return {"result": "Please provide a room name to search for.", "writeup_count": 0}

        gh_results = _search_github(query)
        web_results = _search_web_writeups(query)

        output_lines = [f"# Write-up Search Results for: {query}", ""]

        if gh_results:
            output_lines.append("## GitHub Repositories")
            for r in gh_results[:10]:
                output_lines.append(f"- **{r['name']}** ({r['stars']}★) — {r['url']}")
                if r.get("description"):
                    output_lines.append(f"  {r['description'][:120]}")
            output_lines.append("")

        if web_results:
            output_lines.append("## Web Write-ups")
            for r in web_results[:10]:
                output_lines.append(f"- [{r['title']}]({r['url']})")
            output_lines.append("")

        if not gh_results and not web_results:
            output_lines.append("No write-ups found. Try different search terms.")

        output_lines.append(f"\nTotal: {len(gh_results)} GitHub repos, {len(web_results)} web write-ups")
        output_lines.append(f"\nTo ingest these results, run: ingest_github {query}")

        return {
            "result": "\n".join(output_lines),
            "writeup_count": len(gh_results) + len(web_results),
        }

    # ── ingest ───────────────────────────────────────────────────────────
    elif command.startswith("ingest "):
        target_url = command[7:].strip() or url
        if not target_url:
            return {"result": "Please provide a URL to ingest.", "writeup_count": 0}

        content = _fetch_url(target_url, timeout=min(timeout, 30))
        if not content:
            return {"result": f"Failed to fetch URL: {target_url}", "writeup_count": 0}

        parsed = _parse_writeup(content, target_url)
        room_key = (parsed.get("room_name") or "unknown").lower().replace(" ", "_")

        if room_key not in db.setdefault("rooms", {}):
            db["rooms"][room_key] = {"name": parsed.get("room_name", "unknown"), "writeups": []}

        db["rooms"][room_key]["writeups"].append(parsed)
        db.setdefault("writeups", []).append(parsed)
        _save_db(db)

        return {
            "result": (
                f"Ingested write-up for '{parsed.get('room_name', 'unknown')}'.\n"
                f"Flags found: {len(parsed.get('flags', []))}\n"
                f"Steps extracted: {len(parsed.get('steps', []))}\n"
                f"Tools identified: {', '.join(parsed.get('tools_used', [])[:10])}\n"
                f"Vulnerabilities: {', '.join(parsed.get('vulnerabilities', [])[:10])}"
            ),
            "writeup_count": 1,
            "db_size": len(db.get("writeups", [])),
        }

    # ── ingest_github ────────────────────────────────────────────────────
    elif command.startswith("ingest_github "):
        query = command[14:].strip() or room_name
        if not query:
            return {"result": "Please provide a room name.", "writeup_count": 0}

        gh_results = _search_github(query)
        code_results = _search_github_code(query)

        ingested = 0
        output_lines = [f"# GitHub Ingestion for: {query}", ""]

        # Try to fetch README from each repo
        for repo in gh_results[:5]:
            readme_url = f"https://raw.githubusercontent.com/{repo['name']}/master/README.md"
            content = _fetch_url(readme_url, timeout=15)
            if not content:
                readme_url = f"https://raw.githubusercontent.com/{repo['name']}/main/README.md"
                content = _fetch_url(readme_url, timeout=15)

            if content:
                parsed = _parse_writeup(content, repo["url"])
                room_key = (parsed.get("room_name") or query).lower().replace(" ", "_")

                if room_key not in db.setdefault("rooms", {}):
                    db["rooms"][room_key] = {"name": parsed.get("room_name", query), "writeups": []}

                db["rooms"][room_key]["writeups"].append(parsed)
                db.setdefault("writeups", []).append(parsed)
                ingested += 1
                output_lines.append(f"✓ Ingested: {repo['name']} — {len(parsed.get('steps', []))} steps, {len(parsed.get('flags', []))} flags")

        # Try to fetch individual code files
        for code in code_results[:5]:
            raw_url = f"https://raw.githubusercontent.com/{code['name']}/master/{code['path']}"
            content = _fetch_url(raw_url, timeout=15)
            if not content:
                raw_url = f"https://raw.githubusercontent.com/{code['name']}/main/{code['path']}"
                content = _fetch_url(raw_url, timeout=15)

            if content and len(content) > 200:
                parsed = _parse_writeup(content, code["url"])
                room_key = (parsed.get("room_name") or query).lower().replace(" ", "_")

                if room_key not in db.setdefault("rooms", {}):
                    db["rooms"][room_key] = {"name": parsed.get("room_name", query), "writeups": []}

                db["rooms"][room_key]["writeups"].append(parsed)
                db.setdefault("writeups", []).append(parsed)
                ingested += 1
                output_lines.append(f"✓ Ingested code: {code['name']}/{code['path']}")

        _save_db(db)
        output_lines.append(f"\nTotal ingested: {ingested} write-ups")
        output_lines.append(f"Database now has {len(db.get('writeups', []))} total write-ups across {len(db.get('rooms', {}))} rooms")

        return {
            "result": "\n".join(output_lines),
            "writeup_count": ingested,
            "db_size": len(db.get("writeups", [])),
        }

    # ── fingerprint ──────────────────────────────────────────────────────
    elif command.startswith("fingerprint "):
        target = command[12:].strip() or target_ip
        if not target:
            return {"result": "Please provide a target IP.", "confidence": 0}

        fp = await _fingerprint_target(target)
        _session["target"] = target
        _session["room_identified"] = fp.get("best_match")

        lines = [f"# Fingerprint Results for {target}", ""]
        lines.append(f"Open ports: {', '.join(map(str, fp.get('open_ports', [])))}")
        lines.append("")

        if fp.get("room_candidates"):
            lines.append("## Room Candidates (by confidence)")
            for c in fp["room_candidates"][:10]:
                bar = "█" * int(c["score"] * 20) + "░" * (20 - int(c["score"] * 20))
                lines.append(f"  {bar} {c['score']:.0%} — {c['room_name']} ({c['difficulty']})")
            lines.append("")

        if fp.get("best_match"):
            lines.append(f"**Best match: {fp['best_match']}** (confidence: {fp['confidence']:.0%})")
            lines.append(f"\nTo auto-exploit: auto_exploit {target}")
            lines.append(f"To see write-up: db_show {fp['best_match']}")

        return {
            "result": "\n".join(lines),
            "room_identified": fp.get("best_match"),
            "confidence": fp.get("confidence", 0),
        }

    # ── auto_exploit ─────────────────────────────────────────────────────
    elif command.startswith("auto_exploit "):
        target = command[13:].strip() or target_ip
        if not target:
            return {"result": "Please provide a target IP.", "steps_executed": 0}

        result = await _auto_exploit(target, room_name=room_name or _session.get("room_identified"))
        _session["flags_captured"].extend(result.get("flags_captured", []))
        _session["steps_executed"] += result.get("steps_executed", 0)

        return result

    # ── kotb_speedrun ────────────────────────────────────────────────────
    elif command.startswith("kotb_speedrun "):
        target = command[14:].strip() or target_ip
        if not target:
            return {"result": "Please provide a target IP.", "steps_executed": 0}

        result = await _auto_exploit(target, room_name=room_name or _session.get("room_identified"), speedrun=True)
        _session["flags_captured"].extend(result.get("flags_captured", []))
        _session["steps_executed"] += result.get("steps_executed", 0)

        return result

    # ── db_list ──────────────────────────────────────────────────────────
    elif command == "db_list":
        rooms = db.get("rooms", {})
        if not rooms:
            return {"result": "Database is empty. Use 'ingest_github <room_name>' to populate it.", "db_size": 0}

        lines = [f"# Write-up Database ({len(rooms)} rooms, {len(db.get('writeups', []))} write-ups)", ""]
        for room_key, room_data in sorted(rooms.items()):
            wu_count = len(room_data.get("writeups", []))
            name = room_data.get("name", room_key)
            lines.append(f"  • {name} ({wu_count} write-ups)")

        return {"result": "\n".join(lines), "db_size": len(db.get("writeups", []))}

    # ── db_search ────────────────────────────────────────────────────────
    elif command.startswith("db_search "):
        query = command[10:].strip() or keyword
        if not query:
            return {"result": "Please provide a search keyword.", "writeup_count": 0}

        matches = []
        query_lower = query.lower()
        for wu in db.get("writeups", []):
            wu_str = json.dumps(wu).lower()
            if query_lower in wu_str:
                matches.append(wu)

        if not matches:
            return {"result": f"No matches found for '{query}'.", "writeup_count": 0}

        lines = [f"# Search Results for '{query}' ({len(matches)} matches)", ""]
        for wu in matches[:20]:
            lines.append(f"  • {wu.get('room_name', 'unknown')} — {wu.get('url', '')[:80]}")
            if wu.get("flags"):
                lines.append(f"    Flags: {', '.join(wu['flags'][:5])}")
            if wu.get("vulnerabilities"):
                lines.append(f"    Vulns: {', '.join(wu['vulnerabilities'][:5])}")

        return {"result": "\n".join(lines), "writeup_count": len(matches)}

    # ── db_show ──────────────────────────────────────────────────────────
    elif command.startswith("db_show "):
        query = command[8:].strip() or room_name
        if not query:
            return {"result": "Please provide a room name.", "writeup_count": 0}

        room_key = query.lower().replace(" ", "_")
        room_data = db.get("rooms", {}).get(room_key)

        if not room_data:
            # Try fuzzy match
            for key, data in db.get("rooms", {}).items():
                if query.lower() in key or query.lower() in data.get("name", "").lower():
                    room_data = data
                    room_key = key
                    break

        if not room_data:
            return {"result": f"No write-ups found for '{query}'.", "writeup_count": 0}

        lines = [f"# Write-up: {room_data.get('name', room_key)}", ""]
        for i, wu in enumerate(room_data.get("writeups", [])):
            lines.append(f"## Write-up {i+1}: {wu.get('url', '')}")
            lines.append("")
            if wu.get("flags"):
                lines.append("### Flags")
                for flag in wu["flags"]:
                    lines.append(f"  - `{flag}`")
                lines.append("")
            if wu.get("vulnerabilities"):
                lines.append("### Vulnerabilities")
                for vuln in wu["vulnerabilities"]:
                    lines.append(f"  - {vuln}")
                lines.append("")
            if wu.get("tools_used"):
                lines.append("### Tools Used")
                lines.append(f"  {', '.join(wu['tools_used'][:20])}")
                lines.append("")
            if wu.get("steps"):
                lines.append("### Steps")
                for j, step in enumerate(wu["steps"][:30]):
                    lines.append(f"  {j+1}. {step}")
                lines.append("")
            if wu.get("privesc_method"):
                lines.append(f"### Privilege Escalation")
                lines.append(f"  {wu['privesc_method']}")
                lines.append("")

        return {"result": "\n".join(lines), "writeup_count": len(room_data.get("writeups", []))}

    # ── db_stats ─────────────────────────────────────────────────────────
    elif command == "db_stats":
        rooms = db.get("rooms", {})
        writeups = db.get("writeups", [])
        total_flags = sum(len(wu.get("flags", [])) for wu in writeups)
        total_steps = sum(len(wu.get("steps", [])) for wu in writeups)
        all_tools = set()
        all_vulns = set()
        for wu in writeups:
            all_tools.update(wu.get("tools_used", []))
            all_vulns.update(wu.get("vulnerabilities", []))

        lines = [
            "# Write-up Database Statistics",
            "",
            f"  Total rooms: {len(rooms)}",
            f"  Total write-ups: {len(writeups)}",
            f"  Total flags: {total_flags}",
            f"  Total steps: {total_steps}",
            f"  Unique tools: {len(all_tools)}",
            f"  Unique vulnerabilities: {len(all_vulns)}",
            f"  Last updated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(db.get('last_updated', 0))) if db.get('last_updated') else 'Never'}",
            "",
            "## Top Rooms (by write-up count)",
        ]

        top_rooms = sorted(rooms.items(), key=lambda x: len(x[1].get("writeups", [])), reverse=True)
        for room_key, room_data in top_rooms[:10]:
            lines.append(f"  • {room_data.get('name', room_key)}: {len(room_data.get('writeups', []))} write-ups")

        return {"result": "\n".join(lines), "db_size": len(writeups)}

    # ── db_export ────────────────────────────────────────────────────────
    elif command.startswith("db_export "):
        export_path = command[10:].strip() or path or str(_DB_DIR / "export.json")
        try:
            Path(export_path).write_text(json.dumps(db, indent=2))
            return {"result": f"Database exported to {export_path} ({len(db.get('writeups', []))} write-ups)."}
        except Exception as e:
            return {"result": f"Export failed: {e}"}

    # ── db_import ────────────────────────────────────────────────────────
    elif command.startswith("db_import "):
        import_path = command[10:].strip() or path
        if not import_path:
            return {"result": "Please provide a path to import from."}
        try:
            imported = json.loads(Path(import_path).read_text())
            # Merge into existing DB
            for room_key, room_data in imported.get("rooms", {}).items():
                if room_key not in db.setdefault("rooms", {}):
                    db["rooms"][room_key] = room_data
                else:
                    db["rooms"][room_key].setdefault("writeups", []).extend(
                        room_data.get("writeups", [])
                    )
            db.setdefault("writeups", []).extend(imported.get("writeups", []))
            _save_db(db)
            return {"result": f"Imported {len(imported.get('writeups', []))} write-ups. DB now has {len(db.get('writeups', []))} total."}
        except Exception as e:
            return {"result": f"Import failed: {e}"}

    # ── build_index ──────────────────────────────────────────────────────
    elif command == "build_index":
        index: Dict[str, Any] = {}
        for room_name, patterns, ports, services, difficulty in _ROOM_FINGERPRINTS:
            index[room_name] = {
                "patterns": patterns,
                "ports": ports,
                "services": services,
                "difficulty": difficulty,
            }
        _save_index(index)
        return {"result": f"Fingerprint index rebuilt with {len(index)} rooms."}

    # ── check_tools ──────────────────────────────────────────────────────
    elif command == "check_tools":
        tools_to_check = [
            "nmap", "gobuster", "nikto", "hydra", "john", "hashcat",
            "sqlmap", "enum4linux", "smbclient", "smbmap", "crackmapexec",
            "evil-winrm", "netcat", "socat", "chisel", "searchsploit",
            "msfconsole", "dirb", "ffuf", "wfuzz", "linpeas", "winpeas",
        ]
        available = []
        missing = []
        for tool in tools_to_check:
            if _has_tool(tool):
                available.append(tool)
            else:
                missing.append(tool)

        lines = [
            "# CTF Tools Check",
            "",
            f"## Available ({len(available)})",
            "  " + ", ".join(available),
            "",
            f"## Missing ({len(missing)})",
            "  " + ", ".join(missing),
            "",
            "Install missing tools with:",
            "  sudo apt install nmap gobuster nikto hydra john hashcat sqlmap enum4linux smbclient smbmap crackmapexec evil-winrm netcat-openbsd socat dirb ffuf",
            "  sudo apt install searchsploit metasploit-framework",
            "  # linpeas/winpeas: download from https://github.com/carlospolop/PEASS-ng/releases",
        ]
        return {"result": "\n".join(lines)}

    else:
        return {
            "result": (
                f"Unknown command: '{command}'\n\n"
                "Available commands:\n"
                "  search <room_name>       — Search GitHub + web for write-ups\n"
                "  ingest <url>             — Fetch and parse a write-up URL\n"
                "  ingest_github <name>     — Auto-search GitHub and ingest write-ups\n"
                "  fingerprint <ip>         — Fingerprint target to identify room\n"
                "  auto_exploit <ip>        — Auto-exploit using write-up knowledge\n"
                "  kotb_speedrun <ip>       — KOTH speed-run mode\n"
                "  db_list                  — List all rooms in database\n"
                "  db_search <keyword>      — Search the database\n"
                "  db_show <room_name>      — Show full write-up for a room\n"
                "  db_stats                 — Database statistics\n"
                "  db_export <path>         — Export database to JSON\n"
                "  db_import <path>         — Import database from JSON\n"
                "  build_index              — Rebuild fingerprint index\n"
                "  check_tools              — Check available CTF tools"
            ),
        }


async def description() -> str:
    return (
        "Search GitHub and the web for TryHackMe CTF write-ups, build a local "
        "knowledge database, fingerprint target machines to identify rooms, and "
        "auto-exploit based on known solutions. Optimized for King of the Hill speed runs."
    )


async def prompt() -> str:
    return (
        "Use this tool to search for TryHackMe write-ups, build a knowledge database, "
        "fingerprint targets, and auto-exploit CTF boxes. For KOTH, use kotb_speedrun "
        "for maximum speed."
    )

"""Port of src/utils/suggestions/shellHistoryCompletion.ts - Shell history prefix matching."""
from __future__ import annotations
from typing import Any, Optional, Dict, List
import os
import time
import asyncio

ShellHistoryMatch = Dict[str, Any]

_history_cache: Optional[List[str]] = None
_cache_timestamp: float = 0.0
_CACHE_TTL = 60.0  # seconds


def _detect_shell_history_file() -> Optional[str]:
    """Detect the current shell's history file."""
    shell = os.environ.get('SHELL', '')
    home = os.path.expanduser('~')
    if 'zsh' in shell:
        hist = os.environ.get('HISTFILE') or os.path.join(home, '.zsh_history')
        return hist if os.path.isfile(hist) else None
    if 'fish' in shell:
        hist = os.path.join(home, '.local', 'share', 'fish', 'fish_history')
        return hist if os.path.isfile(hist) else None
    # Default bash
    hist = os.environ.get('HISTFILE') or os.path.join(home, '.bash_history')
    return hist if os.path.isfile(hist) else None


def _parse_history_file(path: str) -> List[str]:
    """Parse a shell history file and return a list of commands (deduped, most recent first)."""
    try:
        with open(path, 'r', errors='replace') as f:
            raw = f.read()
    except OSError:
        return []

    lines = raw.splitlines()
    commands: List[str] = []
    shell = os.environ.get('SHELL', '')

    if 'zsh' in shell:
        # zsh history format: ': timestamp:elapsed;command' or plain 'command'
        for line in lines:
            if line.startswith(': '):
                parts = line.split(';', 1)
                if len(parts) > 1:
                    commands.append(parts[1].strip())
            elif line.strip():
                commands.append(line.strip())
    elif 'fish' in shell:
        # fish: '- cmd: command\n  when: timestamp'
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('- cmd:'):
                commands.append(stripped[6:].strip())
    else:
        # bash: plain commands
        commands = [l.strip() for l in lines if l.strip()]

    # Deduplicate while preserving order (most recent last → reverse for "most recent first")
    seen: set = set()
    deduped: List[str] = []
    for cmd in reversed(commands):
        if cmd and cmd not in seen:
            seen.add(cmd)
            deduped.append(cmd)
    return deduped  # most recent first


async def get_shell_history_commands() -> List[str]:
    """Get shell commands from history, with caching."""
    global _history_cache, _cache_timestamp
    now = time.monotonic()
    if _history_cache is not None and now - _cache_timestamp < _CACHE_TTL:
        return _history_cache

    hist_file = _detect_shell_history_file()
    if not hist_file:
        _history_cache = []
        _cache_timestamp = now
        return []

    commands = await asyncio.get_event_loop().run_in_executor(
        None, _parse_history_file, hist_file
    )
    _history_cache = commands
    _cache_timestamp = now
    return commands


getShellHistoryCommands = get_shell_history_commands


def clear_shell_history_cache() -> None:
    """Clear the shell history cache."""
    global _history_cache, _cache_timestamp
    _history_cache = None
    _cache_timestamp = 0.0


clearShellHistoryCache = clear_shell_history_cache


def prepend_to_shell_history_cache(command: str) -> None:
    """Add command to front of cache without flushing. No-op if cache is empty."""
    global _history_cache
    if _history_cache is None:
        return
    if command in _history_cache:
        _history_cache.remove(command)
    _history_cache.insert(0, command)


prependToShellHistoryCache = prepend_to_shell_history_cache


async def get_shell_history_completion(input_text: str) -> Optional[ShellHistoryMatch]:
    """Find the best matching shell command from history that starts with input_text."""
    if not input_text:
        return None
    commands = await get_shell_history_commands()
    query = input_text.lower()
    for cmd in commands:
        if cmd.lower().startswith(query):
            return {
                'command': cmd,
                'completion': cmd[len(input_text):],
                'label': cmd,
            }
    return None


getShellHistoryCompletion = get_shell_history_completion


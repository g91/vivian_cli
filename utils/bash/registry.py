"""
Port of src/utils/bash/registry.ts
Command spec registry (minimal Python implementation without @withfig/autocomplete).
"""
from __future__ import annotations
from functools import lru_cache
from typing import Any, Dict, List, Optional

CommandSpec = Dict[str, Any]
Argument = Dict[str, Any]
Option = Dict[str, Any]

# Built-in specs for common commands
_BUILTIN_SPECS: List[Dict] = [
    {
        "name": "git",
        "subcommands": [
            {"name": "add"}, {"name": "commit"}, {"name": "push"}, {"name": "pull"},
            {"name": "fetch"}, {"name": "clone"}, {"name": "status"}, {"name": "log"},
            {"name": "diff"}, {"name": "branch"}, {"name": "checkout"}, {"name": "merge"},
            {"name": "rebase"}, {"name": "reset"}, {"name": "stash"}, {"name": "tag"},
            {"name": "remote"}, {"name": "show"}, {"name": "blame"}, {"name": "grep"},
            {"name": "bisect"}, {"name": "cherry-pick"}, {"name": "format-patch"},
            {"name": "am"}, {"name": "apply"}, {"name": "archive"}, {"name": "bundle"},
            {"name": "init"}, {"name": "shortlog"}, {"name": "describe"},
            {"name": "config", "args": [{"name": "key"}, {"name": "value", "isOptional": True}]},
            {"name": "worktree"}, {"name": "submodule"}, {"name": "reflog"},
            {"name": "ls-files"}, {"name": "ls-tree"}, {"name": "rev-parse"},
            {"name": "rev-list"}, {"name": "cat-file"}, {"name": "hash-object"},
        ],
        "options": [
            {"name": "-C", "args": {"name": "path"}},
            {"name": "--git-dir", "args": {"name": "path"}},
            {"name": "--work-tree", "args": {"name": "path"}},
        ],
    },
    {
        "name": "npm",
        "subcommands": [
            {"name": "install"}, {"name": "run"}, {"name": "test"}, {"name": "build"},
            {"name": "start"}, {"name": "publish"}, {"name": "pack"}, {"name": "audit"},
            {"name": "update"}, {"name": "outdated"}, {"name": "list"}, {"name": "info"},
        ],
    },
    {
        "name": "docker",
        "subcommands": [
            {"name": "run"}, {"name": "build"}, {"name": "push"}, {"name": "pull"},
            {"name": "ps"}, {"name": "images"}, {"name": "rm"}, {"name": "rmi"},
            {"name": "exec"}, {"name": "logs"}, {"name": "stop"}, {"name": "start"},
            {"name": "compose"},
        ],
    },
    {
        "name": "kubectl",
        "subcommands": [
            {"name": "get"}, {"name": "apply"}, {"name": "delete"}, {"name": "describe"},
            {"name": "logs"}, {"name": "exec"}, {"name": "port-forward"}, {"name": "scale"},
        ],
    },
    {
        "name": "python",
        "args": [{"name": "script", "isScript": True}],
        "options": [
            {"name": "-c", "args": {"name": "code"}},
            {"name": "-m", "args": {"name": "module", "isModule": True}},
        ],
    },
    {
        "name": "python3",
        "args": [{"name": "script", "isScript": True}],
        "options": [
            {"name": "-c", "args": {"name": "code"}},
            {"name": "-m", "args": {"name": "module", "isModule": True}},
        ],
    },
    {"name": "node", "args": [{"name": "script", "isScript": True}], "options": [{"name": "-e", "args": {"name": "code"}}]},
    {"name": "cargo", "subcommands": [{"name": "build"}, {"name": "run"}, {"name": "test"}, {"name": "check"}, {"name": "clippy"}, {"name": "fmt"}]},
    {"name": "make", "args": [{"name": "target", "isVariadic": True}]},
    {"name": "sudo", "args": [{"name": "command", "isCommand": True, "isVariadic": True}]},
    {"name": "timeout", "args": [{"name": "duration"}, {"name": "command", "isCommand": True, "isVariadic": True}]},
    {"name": "nice", "args": [{"name": "command", "isCommand": True}]},
    {"name": "env", "args": [{"name": "command", "isCommand": True}]},
    {"name": "xargs", "options": [{"name": "-I", "args": {"name": "replace"}}, {"name": "-n", "args": {"name": "max-args"}}, {"name": "-P", "args": {"name": "max-procs"}}]},
]

_SPEC_MAP: Dict[str, Dict] = {s["name"]: s for s in _BUILTIN_SPECS}
_LRU_CACHE: Dict[str, Optional[Dict]] = {}


async def load_fig_spec(command):
    """Attempt to load a fig autocomplete spec. Returns None (no autocomplete package)."""
    if not command or "/" in command or "\\" in command:
        return None
    if ".." in command or command.startswith("-"):
        return None
    return None


async def get_command_spec(command):
    """Get the command spec for a command name. Returns None if not found."""
    if command in _LRU_CACHE:
        return _LRU_CACHE[command]
    spec = _SPEC_MAP.get(command) or _SPEC_MAP.get(command.lower())
    if spec is None:
        spec = await load_fig_spec(command)
    _LRU_CACHE[command] = spec
    return spec


getCommandSpec = get_command_spec
loadFigSpec = load_fig_spec

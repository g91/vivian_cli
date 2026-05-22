"""
Port of src/utils/bash/prefix.ts
Command prefix extraction for bash commands.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Callable
from .commands import split_command_deprecated
from .parser import parse_command, extract_command_arguments
from .registry import get_command_spec

NUMERIC = re.compile(r"^\d+$")
ENV_VAR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

WRAPPER_COMMANDS = {"nice"}


def _to_array(val):
    return val if isinstance(val, list) else [val]


def _is_known_subcommand(arg, spec):
    if not spec or not spec.get("subcommands"):
        return False
    for sub in spec["subcommands"]:
        name = sub.get("name", "")
        if isinstance(name, list):
            if arg in name:
                return True
        elif name == arg:
            return True
    if arg is None: return False
    return True


async def get_command_prefix_static(command, recursion_depth=0, wrapper_count=0):
    """Extract a static command prefix for the given bash command."""
    if wrapper_count > 2 or recursion_depth > 10:
        return None

    parsed = await parse_command(command)
    if not parsed:
        return None

    command_node = parsed.commandNode
    if command_node is None:
        return {"commandPrefix": None}

    env_vars = parsed.envVars or []
    cmd_args = extract_command_arguments(command_node)
    if not cmd_args:
        return {"commandPrefix": None}

    cmd, *args = cmd_args
    if not cmd:
        return {"commandPrefix": None}

    spec = await get_command_spec(cmd)
    is_wrapper = (
        cmd in WRAPPER_COMMANDS
        or (spec and spec.get("args") and any(
            a.get("isCommand") for a in _to_array(spec.get("args", []))
        ))
    )

    if is_wrapper and args and _is_known_subcommand(args[0], spec):
        is_wrapper = False

    if is_wrapper:
        prefix = await _handle_wrapper(cmd, args, recursion_depth, wrapper_count)
    else:
        from ..shell.specPrefix import build_prefix
        prefix = await build_prefix(cmd, args, spec)

    if prefix is None and recursion_depth == 0 and is_wrapper:
        return None

    env_prefix = " ".join(env_vars) + " " if env_vars else ""
    return {"commandPrefix": (env_prefix + prefix) if prefix else None}


async def _handle_wrapper(command, args, recursion_depth, wrapper_count):
    spec = await get_command_spec(command)
    if spec and spec.get("args"):
        args_list = _to_array(spec["args"])
        cmd_arg_idx = next(
            (i for i, a in enumerate(args_list) if a.get("isCommand")), -1
        )
        if cmd_arg_idx != -1:
            parts = [command]
            for i in range(len(args)):
                if i == cmd_arg_idx:
                    result = await get_command_prefix_static(
                        " ".join(args[i:]), recursion_depth + 1, wrapper_count + 1
                    )
                    if result and result.get("commandPrefix"):
                        parts.extend(result["commandPrefix"].split(" "))
                        return " ".join(parts)
                    break
                elif args[i] and not args[i].startswith("-") and not ENV_VAR.match(args[i]):
                    parts.append(args[i])

    wrapped = next(
        (a for a in args if not a.startswith("-") and not NUMERIC.match(a) and not ENV_VAR.match(a)),
        None
    )
    if not wrapped:
        return command

    wrapped_idx = args.index(wrapped)
    result = await get_command_prefix_static(
        " ".join(args[wrapped_idx:]), recursion_depth + 1, wrapper_count + 1
    )
    if not result or not result.get("commandPrefix"):
        return None
    return f"{command} {result['commandPrefix']}"


async def get_compound_command_prefixes_static(command, exclude_subcommand=None):
    """Compute prefixes for compound commands (&&/||/;)."""
    subcommands = split_command_deprecated(command)
    if len(subcommands) <= 1:
        result = await get_command_prefix_static(command)
        return [result["commandPrefix"]] if result and result.get("commandPrefix") else []

    prefixes = []
    for subcmd in subcommands:
        trimmed = subcmd.strip()
        if exclude_subcommand and exclude_subcommand(trimmed):
            continue
        result = await get_command_prefix_static(trimmed)
        if result and result.get("commandPrefix"):
            prefixes.append(result["commandPrefix"])

    # Collapse prefixes with same root via word-aligned longest common prefix
    return _collapse_prefixes(prefixes)


def _collapse_prefixes(prefixes):
    if not prefixes:
        return []
    if len(prefixes) == 1:
        return prefixes

    # Group by root word
    from collections import defaultdict
    groups: Dict[str, List[str]] = defaultdict(list)
    for p in prefixes:
        root = p.split()[0] if p else ""
        groups[root].append(p)

    result = []
    for root, group in groups.items():
        if len(group) == 1:
            result.append(group[0])
        else:
            common = longest_common_prefix(group)
            result.append(common)
    return result


def longest_common_prefix(strings):
    """Compute word-aligned longest common prefix."""
    if not strings:
        return ""
    words_list = [s.split() for s in strings]
    min_len = min(len(w) for w in words_list)
    common_words = []
    for i in range(min_len):
        word = words_list[0][i]
        if all(wl[i] == word for wl in words_list):
            common_words.append(word)
        else:
            break
    return " ".join(common_words)


getCommandPrefixStatic = get_command_prefix_static
getCompoundCommandPrefixesStatic = get_compound_command_prefixes_static
longestCommonPrefix = longest_common_prefix

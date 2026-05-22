"""Port of src/utils/powershell/staticPrefix.ts."""
from __future__ import annotations

from .dangerousCmdlets import NEVER_SUGGEST
from .parser import getAllCommands, parsePowerShellCommand
from ..bash.registry import get_command_spec
from ..shell.specPrefix import DEPTH_RULES, buildPrefix, flagTakesArg


async def extractPrefixFromElement(cmd):
    """Extract a static prefix from a single parsed command element."""
    if cmd.get("nameType") == "application":
        return None
    name = cmd.get("name")
    if not name:
        return None
    if name.lower() in NEVER_SUGGEST:
        return None
    if cmd.get("nameType") == "cmdlet":
        return name

    element_types = cmd.get("elementTypes") or []
    if not element_types or element_types[0] != "StringConstant":
        return None
    for index, arg in enumerate(cmd.get("args", [])):
        del arg
        arg_type = element_types[index + 1] if index + 1 < len(element_types) else None
        if arg_type not in {"StringConstant", "Parameter"}:
            return None

    name_lower = name.lower()
    spec = await get_command_spec(name_lower)
    prefix = await buildPrefix(name, cmd.get("args", []), spec)

    arg_index = 0
    for word in prefix.split(" ")[1:]:
        if "\\" in word:
            return None
        args = cmd.get("args", [])
        while arg_index < len(args):
            candidate = args[arg_index]
            if candidate == word:
                break
            if candidate.startswith("-"):
                arg_index += 1
                if (
                    spec
                    and spec.get("options")
                    and arg_index < len(args)
                    and args[arg_index] != word
                    and not args[arg_index].startswith("-")
                    and flagTakesArg(candidate, args[arg_index], spec)
                ):
                    arg_index += 1
                continue
            return None
        if arg_index >= len(args):
            return None
        arg_index += 1

    if " " not in prefix and ((spec and spec.get("subcommands")) or name_lower in DEPTH_RULES):
        return None
    return prefix


async def getCommandPrefixStatic(command):
    """Extract a prefix suggestion for a PowerShell command."""
    parsed = await parsePowerShellCommand(command)
    if not parsed.get("valid"):
        return None
    first_command = next((cmd for cmd in getAllCommands(parsed) if cmd.get("elementType") == "CommandAst"), None)
    if not first_command:
        return {"commandPrefix": None}
    return {"commandPrefix": await extractPrefixFromElement(first_command)}


async def getCompoundCommandPrefixesStatic(command, excludeSubcommand=None):
    """Extract prefixes for all subcommands in a compound PowerShell command."""
    parsed = await parsePowerShellCommand(command)
    if not parsed.get("valid"):
        return []

    commands = [cmd for cmd in getAllCommands(parsed) if cmd.get("elementType") == "CommandAst"]
    if len(commands) <= 1:
        prefix = await extractPrefixFromElement(commands[0]) if commands else None
        return [prefix] if prefix else []

    prefixes: list[str] = []
    for cmd in commands:
        if excludeSubcommand and excludeSubcommand(cmd):
            continue
        prefix = await extractPrefixFromElement(cmd)
        if prefix:
            prefixes.append(prefix)
    if not prefixes:
        return []

    groups: dict[str, list[str]] = {}
    for prefix in prefixes:
        root = prefix.split(" ")[0]
        groups.setdefault(root.lower(), []).append(prefix)

    collapsed: list[str] = []
    for root_lower, group in groups.items():
        lcp = wordAlignedLCP(group)
        word_count = 0 if lcp == "" else lcp.count(" ") + 1
        if word_count <= 1:
            root_spec = await get_command_spec(root_lower)
            if (root_spec and root_spec.get("subcommands")) or root_lower in DEPTH_RULES:
                continue
        collapsed.append(lcp)
    return collapsed


def wordAlignedLCP(strings):
    """Word-aligned longest common prefix. Doesn't chop mid-word."""
    if not strings:
        return ""
    if len(strings) == 1:
        return strings[0]
    first_words = strings[0].split(" ")
    common_word_count = len(first_words)
    for string in strings[1:]:
        words = string.split(" ")
        match_count = 0
        while (
            match_count < common_word_count
            and match_count < len(words)
            and words[match_count].lower() == first_words[match_count].lower()
        ):
            match_count += 1
        common_word_count = match_count
        if common_word_count == 0:
            break
    return " ".join(first_words[:common_word_count])


extract_prefix_from_element = extractPrefixFromElement
get_command_prefix_static = getCommandPrefixStatic
get_compound_command_prefixes_static = getCompoundCommandPrefixesStatic
word_aligned_lcp = wordAlignedLCP


"""
passpasspasspasspass of src/utils/specPrefix
"""
from __future__ import annotations

from typing import Any


URL_PROTOCOLS = ["http://", "https://", "ftp://"]

# Overrides for commands whose fig specs aren't available at runtime.
DEPTH_RULES: dict[str, int] = {
    "rg": 2,
    "pre-commit": 2,
    "gcloud": 4,
    "gcloud compute": 6,
    "gcloud beta": 6,
    "aws": 4,
    "az": 4,
    "kubectl": 3,
    "docker": 3,
    "dotnet": 3,
    "git push": 2,
}


def _to_array(val: Any) -> list[Any]:
    return val if isinstance(val, list) else [val]


def isKnownSubcommand(arg: str, spec: dict[str, Any] | None) -> bool:
    if not spec or not spec.get("subcommands"):
        return False
    arg_lower = arg.lower()
    for sub in spec["subcommands"]:
        name = sub.get("name")
        if isinstance(name, list):
            if any(str(item).lower() == arg_lower for item in name):
                return True
        elif isinstance(name, str) and name.lower() == arg_lower:
            return True
    return False


def flagTakesArg(flag: str, nextArg: str | None, spec: dict[str, Any] | None) -> bool:
    if spec and spec.get("options"):
        for option in spec["options"]:
            name = option.get("name")
            if isinstance(name, list):
                matches = flag in name
            else:
                matches = name == flag
            if matches:
                return bool(option.get("args"))
    if spec and spec.get("subcommands") and nextArg and not nextArg.startswith("-"):
        return not isKnownSubcommand(nextArg, spec)
    return False


def findFirstSubcommand(args: list[str], spec: dict[str, Any] | None) -> str | None:
    index = 0
    while index < len(args):
        arg = args[index]
        if not arg:
            index += 1
            continue
        if arg.startswith("-"):
            if flagTakesArg(arg, args[index + 1] if index + 1 < len(args) else None, spec):
                index += 2
            else:
                index += 1
            continue
        if not spec or not spec.get("subcommands"):
            return arg
        if isKnownSubcommand(arg, spec):
            return arg
        index += 1
    return None


async def buildPrefix(command: str, args: list[str], spec: dict[str, Any] | None) -> str:
    max_depth = await calculateDepth(command, args, spec)
    parts = [command]
    has_subcommands = bool(spec and spec.get("subcommands"))
    found_subcommand = False

    index = 0
    while index < len(args):
        arg = args[index]
        if not arg or len(parts) >= max_depth:
            break

        if arg.startswith("-"):
            if arg == "-c" and command.lower() in {"python", "python3"}:
                break

            if spec and spec.get("options"):
                for option in spec["options"]:
                    name = option.get("name")
                    matches = arg in name if isinstance(name, list) else name == arg
                    if not matches or not option.get("args"):
                        continue
                    if any(a.get("isCommand") or a.get("isModule") for a in _to_array(option.get("args")) if isinstance(a, dict)):
                        parts.append(arg)
                        index += 1
                        break
                else:
                    if has_subcommands and not found_subcommand:
                        if flagTakesArg(arg, args[index + 1] if index + 1 < len(args) else None, spec):
                            index += 2
                            continue
                        index += 1
                        continue
                    break
                continue

            if has_subcommands and not found_subcommand:
                if flagTakesArg(arg, args[index + 1] if index + 1 < len(args) else None, spec):
                    index += 2
                else:
                    index += 1
                continue
            break

        if await shouldStopAtArg(arg, args[:index], spec):
            break
        if has_subcommands and not found_subcommand:
            found_subcommand = isKnownSubcommand(arg, spec)
        parts.append(arg)
        index += 1

    return " ".join(parts)


async def calculateDepth(command: str, args: list[str], spec: dict[str, Any] | None) -> int:
    first_subcommand = findFirstSubcommand(args, spec)
    command_lower = command.lower()
    key = f"{command_lower} {first_subcommand.lower()}" if first_subcommand else command_lower
    if key in DEPTH_RULES:
        return DEPTH_RULES[key]
    if command_lower in DEPTH_RULES:
        return DEPTH_RULES[command_lower]
    if not spec:
        return 2

    if spec.get("options") and any(arg.startswith("-") for arg in args if arg):
        for arg in args:
            if not arg or not arg.startswith("-"):
                continue
            for option in spec["options"]:
                name = option.get("name")
                matches = arg in name if isinstance(name, list) else name == arg
                if not matches or not option.get("args"):
                    continue
                if any(a.get("isCommand") or a.get("isModule") for a in _to_array(option.get("args")) if isinstance(a, dict)):
                    return 3

    if first_subcommand and spec.get("subcommands"):
        first_sub_lower = first_subcommand.lower()
        subcommand = None
        for sub in spec["subcommands"]:
            name = sub.get("name")
            if isinstance(name, list):
                matches = any(str(item).lower() == first_sub_lower for item in name)
            else:
                matches = isinstance(name, str) and name.lower() == first_sub_lower
            if matches:
                subcommand = sub
                break
        if subcommand:
            if subcommand.get("args"):
                sub_args = _to_array(subcommand.get("args"))
                if any(isinstance(arg, dict) and arg.get("isCommand") for arg in sub_args):
                    return 3
                if any(isinstance(arg, dict) and arg.get("isVariadic") for arg in sub_args):
                    return 2
            if subcommand.get("subcommands"):
                return 4
            if not subcommand.get("args"):
                return 2
            return 3

    if spec.get("args"):
        args_array = _to_array(spec.get("args"))
        if any(isinstance(arg, dict) and arg.get("isCommand") for arg in args_array):
            if not isinstance(spec.get("args"), list) and isinstance(spec.get("args"), dict) and spec["args"].get("isCommand"):
                return 2
            first_command_index = next(
                (index for index, arg in enumerate(args_array) if isinstance(arg, dict) and arg.get("isCommand")),
                -1,
            )
            return min(2 + first_command_index, 3)

        if not spec.get("subcommands"):
            if any(isinstance(arg, dict) and arg.get("isVariadic") for arg in args_array):
                return 1
            if args_array and isinstance(args_array[0], dict) and not args_array[0].get("isOptional"):
                return 2

    if spec.get("args") and any(isinstance(arg, dict) and arg.get("isDangerous") for arg in _to_array(spec.get("args"))):
        return 3
    return 2


async def shouldStopAtArg(arg: str, args: list[str], spec: dict[str, Any] | None) -> bool:
    if arg.startswith("-"):
        return True

    dot_index = arg.rfind(".")
    has_extension = dot_index > 0 and dot_index < len(arg) - 1 and ":" not in arg[dot_index + 1:]
    has_file = "/" in arg or has_extension
    has_url = any(arg.startswith(proto) for proto in URL_PROTOCOLS)

    if not has_file and not has_url:
        return False

    if spec and spec.get("options") and args and args[-1] == "-m":
        for option in spec["options"]:
            name = option.get("name")
            matches = "-m" in name if isinstance(name, list) else name == "-m"
            if not matches or not option.get("args"):
                continue
            if any(isinstance(a, dict) and a.get("isModule") for a in _to_array(option.get("args"))):
                return False

    return True


build_prefix = buildPrefix
calculate_depth = calculateDepth
should_stop_at_arg = shouldStopAtArg
is_known_subcommand = isKnownSubcommand
flag_takes_arg = flagTakesArg
find_first_subcommand = findFirstSubcommand


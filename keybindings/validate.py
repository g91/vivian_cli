"""Keybinding validation — mirrors src/keybindings/validate.ts."""
from __future__ import annotations

import re
from typing import Any

from ..utils.stringUtils import plural
from .parser import KeybindingBlock, ParsedBinding, chordToString, parseChord, parseKeystroke
from .reservedShortcuts import getReservedShortcuts, normalizeKeyForComparison
from .schema import KEYBINDING_CONTEXTS


KeybindingWarning = dict[str, Any]


def isKeybindingBlock(obj: Any) -> bool:
    return (
        isinstance(obj, dict)
        and isinstance(obj.get("context"), str)
        and isinstance(obj.get("bindings"), dict)
    )


def isKeybindingBlockArray(arr: Any) -> bool:
    return isinstance(arr, list) and all(isKeybindingBlock(item) for item in arr)


VALID_CONTEXTS = list(KEYBINDING_CONTEXTS)


def isValidContext(value: str) -> bool:
    return value in VALID_CONTEXTS


def validateKeystroke(keystroke: str) -> KeybindingWarning | None:
    parts = keystroke.lower().split("+")
    for part in parts:
        trimmed = part.strip()
        if not trimmed:
            return {
                "type": "parse_error",
                "severity": "error",
                "message": f'Empty key part in "{keystroke}"',
                "key": keystroke,
                "suggestion": 'Remove extra "+" characters',
            }

    parsed = parseKeystroke(keystroke)
    if not parsed.key and not parsed.ctrl and not parsed.alt and not parsed.shift and not parsed.meta:
        return {
            "type": "parse_error",
            "severity": "error",
            "message": f'Could not parse keystroke "{keystroke}"',
            "key": keystroke,
        }

    return None


def validateBlock(block: Any, blockIndex: int) -> list[KeybindingWarning]:
    warnings: list[KeybindingWarning] = []
    if not isinstance(block, dict):
        warnings.append(
            {
                "type": "parse_error",
                "severity": "error",
                "message": f"Keybinding block {blockIndex + 1} is not an object",
            }
        )
        return warnings

    raw_context = block.get("context")
    context_name: str | None = None
    if not isinstance(raw_context, str):
        warnings.append(
            {
                "type": "parse_error",
                "severity": "error",
                "message": f'Keybinding block {blockIndex + 1} missing "context" field',
            }
        )
    elif not isValidContext(raw_context):
        warnings.append(
            {
                "type": "invalid_context",
                "severity": "error",
                "message": f'Unknown context "{raw_context}"',
                "context": raw_context,
                "suggestion": f'Valid contexts: {", ".join(VALID_CONTEXTS)}',
            }
        )
    else:
        context_name = raw_context

    bindings = block.get("bindings")
    if not isinstance(bindings, dict):
        warnings.append(
            {
                "type": "parse_error",
                "severity": "error",
                "message": f'Keybinding block {blockIndex + 1} missing "bindings" field',
            }
        )
        return warnings

    for key, action in bindings.items():
        key_error = validateKeystroke(str(key))
        if key_error is not None:
            key_error["context"] = context_name
            warnings.append(key_error)

        if action is not None and not isinstance(action, str):
            warnings.append(
                {
                    "type": "invalid_action",
                    "severity": "error",
                    "message": f'Invalid action for "{key}": must be a string or null',
                    "key": key,
                    "context": context_name,
                }
            )
        elif isinstance(action, str) and action.startswith("command:"):
            if re.fullmatch(r"command:[a-zA-Z0-9:\-_]+", action) is None:
                warnings.append(
                    {
                        "type": "invalid_action",
                        "severity": "warning",
                        "message": f'Invalid command binding "{action}" for "{key}": command name may only contain alphanumeric characters, colons, hyphens, and underscores',
                        "key": key,
                        "context": context_name,
                        "action": action,
                    }
                )
            if context_name and context_name != "Chat":
                warnings.append(
                    {
                        "type": "invalid_action",
                        "severity": "warning",
                        "message": f'Command binding "{action}" must be in "Chat" context, not "{context_name}"',
                        "key": key,
                        "context": context_name,
                        "action": action,
                        "suggestion": 'Move this binding to a block with "context": "Chat"',
                    }
                )
        elif action == "voice:pushToTalk":
            keystroke = parseChord(str(key))[0]
            if (
                keystroke
                and not keystroke.ctrl
                and not keystroke.alt
                and not keystroke.shift
                and not keystroke.meta
                and not keystroke.super
                and re.fullmatch(r"[a-z]", keystroke.key or "")
            ):
                warnings.append(
                    {
                        "type": "invalid_action",
                        "severity": "warning",
                        "message": f'Binding "{key}" to voice:pushToTalk prints into the input during warmup; use space or a modifier combo like meta+k',
                        "key": key,
                        "context": context_name,
                        "action": action,
                    }
                )

    return warnings


def checkDuplicateKeysInJson(jsonString: str) -> list[KeybindingWarning]:
    warnings: list[KeybindingWarning] = []
    bindings_block_pattern = re.compile(r'"bindings"\s*:\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}')
    context_pattern = re.compile(r'"context"\s*:\s*"([^"]+)"[^\{]*$')
    key_pattern = re.compile(r'"([^"]+)"\s*:')

    for block_match in bindings_block_pattern.finditer(jsonString):
        block_content = block_match.group(1)
        if not block_content:
            continue

        text_before_block = jsonString[: block_match.start()]
        context_match = context_pattern.search(text_before_block)
        context = context_match.group(1) if context_match else "unknown"
        keys_by_name: dict[str, int] = {}

        for key_match in key_pattern.finditer(block_content):
            key = key_match.group(1)
            if not key:
                continue
            count = keys_by_name.get(key, 0) + 1
            keys_by_name[key] = count
            if count == 2:
                warnings.append(
                    {
                        "type": "duplicate",
                        "severity": "warning",
                        "message": f'Duplicate key "{key}" in {context} bindings',
                        "key": key,
                        "context": context,
                        "suggestion": "This key appears multiple times in the same context. JSON uses the last value, earlier values are ignored.",
                    }
                )

    return warnings


def validateUserConfig(userBlocks: Any) -> list[KeybindingWarning]:
    warnings: list[KeybindingWarning] = []
    if not isinstance(userBlocks, list):
        warnings.append(
            {
                "type": "parse_error",
                "severity": "error",
                "message": "keybindings.json must contain an array",
                "suggestion": "Wrap your bindings in [ ]",
            }
        )
        return warnings

    for index, block in enumerate(userBlocks):
        warnings.extend(validateBlock(block, index))
    return warnings


def checkDuplicates(blocks: list[KeybindingBlock]) -> list[KeybindingWarning]:
    warnings: list[KeybindingWarning] = []
    seen_by_context: dict[str, dict[str, str]] = {}

    for block in blocks:
        context_map = seen_by_context.setdefault(block.context, {})
        for key, action in block.bindings.items():
            normalized_key = normalizeKeyForComparison(key)
            existing_action = context_map.get(normalized_key)
            current_action = "null" if action is None else str(action)
            if existing_action is not None and existing_action != current_action:
                warnings.append(
                    {
                        "type": "duplicate",
                        "severity": "warning",
                        "message": f'Duplicate binding "{key}" in {block.context} context',
                        "key": key,
                        "context": block.context,
                        "action": current_action,
                        "suggestion": f'Previously bound to "{existing_action}". Only the last binding will be used.',
                    }
                )
            context_map[normalized_key] = current_action

    return warnings


def checkReservedShortcuts(bindings: list[ParsedBinding]) -> list[KeybindingWarning]:
    warnings: list[KeybindingWarning] = []
    reserved = getReservedShortcuts()
    for binding in bindings:
        key_display = chordToString(binding.chord)
        normalized_key = normalizeKeyForComparison(key_display)
        for reserved_shortcut in reserved:
            if normalizeKeyForComparison(reserved_shortcut["key"]) == normalized_key:
                warnings.append(
                    {
                        "type": "reserved",
                        "severity": reserved_shortcut["severity"],
                        "message": f'"{key_display}" may not work: {reserved_shortcut["reason"]}',
                        "key": key_display,
                        "context": binding.context,
                        "action": binding.action,
                    }
                )
    return warnings


def getUserBindingsForValidation(userBlocks: list[KeybindingBlock]) -> list[ParsedBinding]:
    bindings: list[ParsedBinding] = []
    for block in userBlocks:
        for key, action in block.bindings.items():
            bindings.append(ParsedBinding(chord=[parseKeystroke(step) for step in key.split(" ")], action=action, context=block.context))
    return bindings


def _coerce_blocks(userBlocks: Any) -> list[KeybindingBlock] | None:
    if not isKeybindingBlockArray(userBlocks):
        return None
    return [
        KeybindingBlock(context=item["context"], bindings=dict(item["bindings"]))
        for item in userBlocks
    ]


def validateBindings(userBlocks: Any, _parsedBindings: list[ParsedBinding]) -> list[KeybindingWarning]:
    warnings: list[KeybindingWarning] = []
    warnings.extend(validateUserConfig(userBlocks))

    coerced_blocks = _coerce_blocks(userBlocks)
    if coerced_blocks is not None:
        warnings.extend(checkDuplicates(coerced_blocks))
        warnings.extend(checkReservedShortcuts(getUserBindingsForValidation(coerced_blocks)))

    seen: set[str] = set()
    deduped: list[KeybindingWarning] = []
    for warning in warnings:
        key = f'{warning.get("type")}:{warning.get("key")}:{warning.get("context")}'
        if key in seen:
            continue
        seen.add(key)
        deduped.append(warning)
    return deduped


def formatWarning(warning: KeybindingWarning) -> str:
    icon = "✗" if warning["severity"] == "error" else "⚠"
    message = f'{icon} Keybinding {warning["severity"]}: {warning["message"]}'
    suggestion = warning.get("suggestion")
    if suggestion:
        message += f'\n  {suggestion}'
    return message


def formatWarnings(warnings: list[KeybindingWarning]) -> str:
    if not warnings:
        return ""

    errors = [warning for warning in warnings if warning["severity"] == "error"]
    warns = [warning for warning in warnings if warning["severity"] == "warning"]
    lines: list[str] = []

    if errors:
        lines.append(f'Found {len(errors)} keybinding {plural(len(errors), "error")}:')
        lines.extend(formatWarning(error) for error in errors)

    if warns:
        if lines:
            lines.append("")
        lines.append(f'Found {len(warns)} keybinding {plural(len(warns), "warning")}:')
        lines.extend(formatWarning(warn) for warn in warns)

    return "\n".join(lines)


is_keybinding_block = isKeybindingBlock
is_keybinding_block_array = isKeybindingBlockArray
is_valid_context = isValidContext
validate_keystroke = validateKeystroke
validate_block = validateBlock
check_duplicate_keys_in_json = checkDuplicateKeysInJson
validate_user_config = validateUserConfig
check_duplicates = checkDuplicates
check_reserved_shortcuts = checkReservedShortcuts
get_user_bindings_for_validation = getUserBindingsForValidation
validate_bindings = validateBindings
format_warning = formatWarning
format_warnings = formatWarnings
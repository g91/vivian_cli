"""Keybinding template generation — mirrors src/keybindings/template.ts."""
from __future__ import annotations

from ..utils.slowOperations import json_stringify
from .defaultBindings import DEFAULT_BINDINGS
from .reservedShortcuts import NON_REBINDABLE, normalizeKeyForComparison
from .parser import KeybindingBlock


def filterReservedShortcuts(blocks: list[KeybindingBlock]) -> list[KeybindingBlock]:
    reserved_keys = {normalizeKeyForComparison(item["key"]) for item in NON_REBINDABLE}
    filtered: list[KeybindingBlock] = []
    for block in blocks:
        filtered_bindings: dict[str, str | None] = {}
        for key, action in block.bindings.items():
            if normalizeKeyForComparison(key) not in reserved_keys:
                filtered_bindings[key] = action
        if filtered_bindings:
            filtered.append(KeybindingBlock(context=block.context, bindings=filtered_bindings))
    return filtered


def generateKeybindingsTemplate() -> str:
    bindings = filterReservedShortcuts(DEFAULT_BINDINGS)
    config = {
        "$schema": "https://www.schemastore.org/vivian-code-keybindings.json",
        "$docs": "https://api-vivian.d0a.net/docs/en/keybindings",
        "bindings": [
            {"context": block.context, "bindings": block.bindings} for block in bindings
        ],
    }
    return json_stringify(config, indent=2) + "\n"


filter_reserved_shortcuts = filterReservedShortcuts
generate_keybindings_template = generateKeybindingsTemplate
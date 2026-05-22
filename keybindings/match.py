"""Keybinding match helpers — mirrors src/keybindings/match.ts."""
from __future__ import annotations

from typing import Any

from .parser import ParsedBinding, ParsedKeystroke


def getInkModifiers(key: dict[str, Any]) -> dict[str, bool]:
    return {
        "ctrl": bool(key.get("ctrl")),
        "shift": bool(key.get("shift")),
        "meta": bool(key.get("meta")),
        "super": bool(key.get("super")),
    }


def getKeyName(input_value: str, key: dict[str, Any]) -> str | None:
    if key.get("escape"):
        return "escape"
    if key.get("return"):
        return "enter"
    if key.get("tab"):
        return "tab"
    if key.get("backspace"):
        return "backspace"
    if key.get("delete"):
        return "delete"
    if key.get("upArrow"):
        return "up"
    if key.get("downArrow"):
        return "down"
    if key.get("leftArrow"):
        return "left"
    if key.get("rightArrow"):
        return "right"
    if key.get("pageUp"):
        return "pageup"
    if key.get("pageDown"):
        return "pagedown"
    if key.get("wheelUp"):
        return "wheelup"
    if key.get("wheelDown"):
        return "wheeldown"
    if key.get("home"):
        return "home"
    if key.get("end"):
        return "end"
    if len(input_value) == 1:
        return input_value.lower()
    return None


def modifiersMatch(ink_mods: dict[str, bool], target: ParsedKeystroke) -> bool:
    if ink_mods["ctrl"] != target.ctrl:
        return False
    if ink_mods["shift"] != target.shift:
        return False
    target_needs_meta = target.alt or target.meta
    if ink_mods["meta"] != target_needs_meta:
        return False
    if ink_mods["super"] != target.super:
        return False
    return True


def matchesKeystroke(input_value: str, key: dict[str, Any], target: ParsedKeystroke) -> bool:
    key_name = getKeyName(input_value, key)
    if key_name != target.key:
        return False
    ink_mods = getInkModifiers(key)
    if key.get("escape"):
        ink_mods = {**ink_mods, "meta": False}
    return modifiersMatch(ink_mods, target)


def matchesBinding(input_value: str, key: dict[str, Any], binding: ParsedBinding) -> bool:
    if len(binding.chord) != 1:
        return False
    keystroke = binding.chord[0]
    return matchesKeystroke(input_value, key, keystroke)


get_ink_modifiers = getInkModifiers
get_key_name = getKeyName
modifiers_match = modifiersMatch
matches_keystroke = matchesKeystroke
matches_binding = matchesBinding
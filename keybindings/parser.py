"""Keybinding parser helpers — mirrors src/keybindings/parser.ts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ParsedKeystroke:
    key: str
    ctrl: bool = False
    alt: bool = False
    shift: bool = False
    meta: bool = False
    super: bool = False


Chord = list[ParsedKeystroke]


@dataclass
class KeybindingBlock:
    context: str
    bindings: dict[str, Any]


@dataclass
class ParsedBinding:
    chord: Chord
    action: Any
    context: str


def parseKeystroke(input_value: str) -> ParsedKeystroke:
    parts = input_value.split("+")
    keystroke = ParsedKeystroke(key="")
    for part in parts:
        lower = part.lower()
        if lower in {"ctrl", "control"}:
            keystroke.ctrl = True
        elif lower in {"alt", "opt", "option"}:
            keystroke.alt = True
        elif lower == "shift":
            keystroke.shift = True
        elif lower == "meta":
            keystroke.meta = True
        elif lower in {"cmd", "command", "super", "win"}:
            keystroke.super = True
        elif lower == "esc":
            keystroke.key = "escape"
        elif lower == "return":
            keystroke.key = "enter"
        elif lower == "space":
            keystroke.key = " "
        elif lower == "↑":
            keystroke.key = "up"
        elif lower == "↓":
            keystroke.key = "down"
        elif lower == "←":
            keystroke.key = "left"
        elif lower == "→":
            keystroke.key = "right"
        else:
            keystroke.key = lower
    return keystroke


def parseChord(input_value: str) -> Chord:
    if input_value == " ":
        return [parseKeystroke("space")]
    return [parseKeystroke(step) for step in input_value.strip().split()]


def keyToDisplayName(key: str) -> str:
    mapping = {
        "escape": "Esc",
        " ": "Space",
        "tab": "tab",
        "enter": "Enter",
        "backspace": "Backspace",
        "delete": "Delete",
        "up": "↑",
        "down": "↓",
        "left": "←",
        "right": "→",
        "pageup": "PageUp",
        "pagedown": "PageDown",
        "home": "Home",
        "end": "End",
    }
    return mapping.get(key, key)


def keystrokeToString(keystroke: ParsedKeystroke) -> str:
    parts: list[str] = []
    if keystroke.ctrl:
        parts.append("ctrl")
    if keystroke.alt:
        parts.append("alt")
    if keystroke.shift:
        parts.append("shift")
    if keystroke.meta:
        parts.append("meta")
    if keystroke.super:
        parts.append("cmd")
    parts.append(keyToDisplayName(keystroke.key))
    return "+".join(parts)


def chordToString(chord: Chord) -> str:
    return " ".join(keystrokeToString(item) for item in chord)


def keystrokeToDisplayString(keystroke: ParsedKeystroke, platform: str = "linux") -> str:
    parts: list[str] = []
    if keystroke.ctrl:
        parts.append("ctrl")
    if keystroke.alt or keystroke.meta:
        parts.append("opt" if platform == "macos" else "alt")
    if keystroke.shift:
        parts.append("shift")
    if keystroke.super:
        parts.append("cmd" if platform == "macos" else "super")
    parts.append(keyToDisplayName(keystroke.key))
    return "+".join(parts)


def chordToDisplayString(chord: Chord, platform: str = "linux") -> str:
    return " ".join(keystrokeToDisplayString(item, platform) for item in chord)


def parseBindings(blocks: list[KeybindingBlock]) -> list[ParsedBinding]:
    bindings: list[ParsedBinding] = []
    for block in blocks:
        for key, action in block.bindings.items():
            bindings.append(ParsedBinding(chord=parseChord(key), action=action, context=block.context))
    return bindings


parse_keystroke = parseKeystroke
parse_chord = parseChord
keystroke_to_string = keystrokeToString
chord_to_string = chordToString
keystroke_to_display_string = keystrokeToDisplayString
chord_to_display_string = chordToDisplayString
parse_bindings = parseBindings
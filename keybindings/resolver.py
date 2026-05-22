"""Keybinding resolver — mirrors src/keybindings/resolver.ts."""
from __future__ import annotations

from typing import Any

from .match import getKeyName, matchesBinding
from .parser import ParsedBinding, ParsedKeystroke, chordToString


def resolveKey(input_value: str, key: dict[str, Any], activeContexts: list[str], bindings: list[ParsedBinding]) -> dict:
    match: ParsedBinding | None = None
    context_set = set(activeContexts)
    for binding in bindings:
        if len(binding.chord) != 1:
            continue
        if binding.context not in context_set:
            continue
        if matchesBinding(input_value, key, binding):
            match = binding
    if match is None:
        return {"type": "none"}
    if match.action is None:
        return {"type": "unbound"}
    return {"type": "match", "action": match.action}


def getBindingDisplayText(action: str, context: str, bindings: list[ParsedBinding]) -> str | None:
    for binding in reversed(bindings):
        if binding.action == action and binding.context == context:
            return chordToString(binding.chord)
    return None


def buildKeystroke(input_value: str, key: dict[str, Any]) -> ParsedKeystroke | None:
    key_name = getKeyName(input_value, key)
    if not key_name:
        return None
    effective_meta = False if key.get("escape") else bool(key.get("meta"))
    return ParsedKeystroke(
        key=key_name,
        ctrl=bool(key.get("ctrl")),
        alt=effective_meta,
        shift=bool(key.get("shift")),
        meta=effective_meta,
        super=bool(key.get("super")),
    )


def keystrokesEqual(left: ParsedKeystroke, right: ParsedKeystroke) -> bool:
    return (
        left.key == right.key
        and left.ctrl == right.ctrl
        and left.shift == right.shift
        and ((left.alt or left.meta) == (right.alt or right.meta))
        and left.super == right.super
    )


def chordPrefixMatches(prefix: list[ParsedKeystroke], binding: ParsedBinding) -> bool:
    if len(prefix) >= len(binding.chord):
        return False
    for index, prefix_key in enumerate(prefix):
        binding_key = binding.chord[index]
        if not keystrokesEqual(prefix_key, binding_key):
            return False
    return True


def chordExactlyMatches(chord: list[ParsedKeystroke], binding: ParsedBinding) -> bool:
    if len(chord) != len(binding.chord):
        return False
    for index, chord_key in enumerate(chord):
        if not keystrokesEqual(chord_key, binding.chord[index]):
            return False
    return True


def resolveKeyWithChordState(
    input_value: str,
    key: dict[str, Any],
    activeContexts: list[str],
    bindings: list[ParsedBinding],
    pending: list[ParsedKeystroke] | None,
) -> dict:
    if key.get("escape") and pending is not None:
        return {"type": "chord_cancelled"}

    current_keystroke = buildKeystroke(input_value, key)
    if current_keystroke is None:
        return {"type": "chord_cancelled"} if pending is not None else {"type": "none"}

    test_chord = [*pending, current_keystroke] if pending else [current_keystroke]
    context_set = set(activeContexts)
    context_bindings = [binding for binding in bindings if binding.context in context_set]

    chord_winners: dict[str, Any] = {}
    for binding in context_bindings:
        if len(binding.chord) > len(test_chord) and chordPrefixMatches(test_chord, binding):
            chord_winners[chordToString(binding.chord)] = binding.action
    has_longer_chords = any(action is not None for action in chord_winners.values())
    if has_longer_chords:
        return {"type": "chord_started", "pending": test_chord}

    exact_match: ParsedBinding | None = None
    for binding in context_bindings:
        if chordExactlyMatches(test_chord, binding):
            exact_match = binding
    if exact_match is not None:
        if exact_match.action is None:
            return {"type": "unbound"}
        return {"type": "match", "action": exact_match.action}

    if pending is not None:
        return {"type": "chord_cancelled"}
    return {"type": "none"}


resolve_key = resolveKey
get_binding_display_text = getBindingDisplayText
build_keystroke = buildKeystroke
keystrokes_equal = keystrokesEqual
resolve_key_with_chord_state = resolveKeyWithChordState
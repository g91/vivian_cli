"""Keybinding types — mirrors src/keybindings/types.ts."""
from __future__ import annotations

from typing import Literal, TypeAlias, TypedDict

from .parser import Chord, KeybindingBlock, ParsedBinding, ParsedKeystroke

KeybindingContextName: TypeAlias = str


class ChordStartedResult(TypedDict):
    type: Literal["chord_started"]
    pending: list[ParsedKeystroke]


class MatchResult(TypedDict):
    type: Literal["match"]
    action: str


class UnboundResult(TypedDict):
    type: Literal["unbound"]


class ChordCancelledResult(TypedDict):
    type: Literal["chord_cancelled"]


class NoneResult(TypedDict):
    type: Literal["none"]


ChordResolveResult: TypeAlias = (
    ChordStartedResult | MatchResult | UnboundResult | ChordCancelledResult | NoneResult
)

__all__ = [
    "Chord",
    "ChordResolveResult",
    "ChordStartedResult",
    "KeybindingBlock",
    "KeybindingContextName",
    "MatchResult",
    "NoneResult",
    "ParsedBinding",
    "ParsedKeystroke",
    "UnboundResult",
    "ChordCancelledResult",
]
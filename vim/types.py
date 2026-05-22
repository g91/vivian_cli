"""Vim mode state machine types — mirrors src/vim/types.ts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict

Operator = Literal["delete", "change", "yank"]
FindType = Literal["f", "F", "t", "T"]
TextObjScope = Literal["inner", "around"]

VoiceLikeMode = Literal["INSERT", "NORMAL"]


@dataclass
class VimState:
    mode: VoiceLikeMode
    insertedText: str | None = None
    command: dict | None = None


@dataclass
class PersistentState:
    lastChange: dict | None = None
    lastFind: dict | None = None
    register: str = ""
    registerIsLinewise: bool = False


class OperatorMap(TypedDict):
    d: Literal["delete"]
    c: Literal["change"]
    y: Literal["yank"]


OPERATORS: OperatorMap = {
    "d": "delete",
    "c": "change",
    "y": "yank",
}


def isOperatorKey(key: str) -> bool:
    return key in OPERATORS


SIMPLE_MOTIONS = {
    "h",
    "l",
    "j",
    "k",
    "w",
    "b",
    "e",
    "W",
    "B",
    "E",
    "0",
    "^",
    "$",
}

FIND_KEYS = {"f", "F", "t", "T"}

TEXT_OBJ_SCOPES: dict[str, TextObjScope] = {
    "i": "inner",
    "a": "around",
}


def isTextObjScopeKey(key: str) -> bool:
    return key in TEXT_OBJ_SCOPES


TEXT_OBJ_TYPES = {
    "w",
    "W",
    '"',
    "'",
    "`",
    "(",
    ")",
    "b",
    "[",
    "]",
    "{",
    "}",
    "B",
    "<",
    ">",
}

MAX_VIM_COUNT = 10000


def createInitialVimState() -> VimState:
    return VimState(mode="INSERT", insertedText="")


def createInitialPersistentState() -> PersistentState:
    return PersistentState()


create_initial_vim_state = createInitialVimState
create_initial_persistent_state = createInitialPersistentState
is_operator_key = isOperatorKey
is_text_obj_scope_key = isTextObjScopeKey
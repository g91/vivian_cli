"""Vim transition table — mirrors src/vim/transitions.ts."""
from __future__ import annotations

from typing import Any

from .motions import resolveMotion
from .operators import (
    executeIndent,
    executeJoin,
    executeLineOp,
    executeOpenLine,
    executeOperatorFind,
    executeOperatorG,
    executeOperatorGg,
    executeOperatorMotion,
    executeOperatorTextObj,
    executePaste,
    executeReplace,
    executeToggleCase,
    executeX,
)
from .types import FIND_KEYS, MAX_VIM_COUNT, OPERATORS, SIMPLE_MOTIONS, TEXT_OBJ_SCOPES, TEXT_OBJ_TYPES, isOperatorKey, isTextObjScopeKey


def transition(state: dict, input: str, ctx: Any) -> dict:
    state_type = state.get("type")
    if state_type == "idle":
        return fromIdle(input, ctx)
    if state_type == "count":
        return fromCount(state, input, ctx)
    if state_type == "operator":
        return fromOperator(state, input, ctx)
    if state_type == "operatorCount":
        return fromOperatorCount(state, input, ctx)
    if state_type == "operatorFind":
        return fromOperatorFind(state, input, ctx)
    if state_type == "operatorTextObj":
        return fromOperatorTextObj(state, input, ctx)
    if state_type == "find":
        return fromFind(state, input, ctx)
    if state_type == "g":
        return fromG(state, input, ctx)
    if state_type == "operatorG":
        return fromOperatorG(state, input, ctx)
    if state_type == "replace":
        return fromReplace(state, input, ctx)
    if state_type == "indent":
        return fromIndent(state, input, ctx)
    return {}


def handleNormalInput(input: str, count: int, ctx: Any) -> dict | None:
    if isOperatorKey(input):
        return {"next": {"type": "operator", "op": OPERATORS[input], "count": count}}
    if input in SIMPLE_MOTIONS:
        return {"execute": lambda: ctx.setOffset(resolveMotion(input, ctx.cursor, count).offset)}
    if input in FIND_KEYS:
        return {"next": {"type": "find", "find": input, "count": count}}
    if input == "g":
        return {"next": {"type": "g", "count": count}}
    if input == "r":
        return {"next": {"type": "replace", "count": count}}
    if input in {">", "<"}:
        return {"next": {"type": "indent", "dir": input, "count": count}}
    if input == "~":
        return {"execute": lambda: executeToggleCase(count, ctx)}
    if input == "x":
        return {"execute": lambda: executeX(count, ctx)}
    if input == "J":
        return {"execute": lambda: executeJoin(count, ctx)}
    if input in {"p", "P"}:
        return {"execute": lambda: executePaste(input == "p", count, ctx)}
    if input == "D":
        return {"execute": lambda: executeOperatorMotion("delete", "$", 1, ctx)}
    if input == "C":
        return {"execute": lambda: executeOperatorMotion("change", "$", 1, ctx)}
    if input == "Y":
        return {"execute": lambda: executeLineOp("yank", count, ctx)}
    if input == "G":
        def _go() -> None:
            if count == 1:
                ctx.setOffset(ctx.cursor.startOfLastLine().offset)
            else:
                ctx.setOffset(ctx.cursor.goToLine(count).offset)
        return {"execute": _go}
    if input == ".":
        return {"execute": lambda: getattr(ctx, "onDotRepeat", lambda: None)()}
    if input in {";", ","}:
        return {"execute": lambda: executeRepeatFind(input == ",", count, ctx)}
    if input == "u":
        return {"execute": lambda: getattr(ctx, "onUndo", lambda: None)()}
    if input == "i":
        return {"execute": lambda: ctx.enterInsert(ctx.cursor.offset)}
    if input == "I":
        return {"execute": lambda: ctx.enterInsert(ctx.cursor.firstNonBlankInLogicalLine().offset)}
    if input == "a":
        def _append() -> None:
            new_offset = ctx.cursor.offset if ctx.cursor.isAtEnd() else ctx.cursor.right().offset
            ctx.enterInsert(new_offset)
        return {"execute": _append}
    if input == "A":
        return {"execute": lambda: ctx.enterInsert(ctx.cursor.endOfLogicalLine().offset)}
    if input == "o":
        return {"execute": lambda: executeOpenLine("below", ctx)}
    if input == "O":
        return {"execute": lambda: executeOpenLine("above", ctx)}
    return None


def handleOperatorInput(op: str, count: int, input: str, ctx: Any) -> dict | None:
    if isTextObjScopeKey(input):
        return {"next": {"type": "operatorTextObj", "op": op, "count": count, "scope": TEXT_OBJ_SCOPES[input]}}
    if input in FIND_KEYS:
        return {"next": {"type": "operatorFind", "op": op, "count": count, "find": input}}
    if input in SIMPLE_MOTIONS:
        return {"execute": lambda: executeOperatorMotion(op, input, count, ctx)}
    if input == "G":
        return {"execute": lambda: executeOperatorG(op, count, ctx)}
    if input == "g":
        return {"next": {"type": "operatorG", "op": op, "count": count}}
    return None


def fromIdle(input: str, ctx: Any) -> dict:
    if input.isdigit() and input != "0":
        return {"next": {"type": "count", "digits": input}}
    if input == "0":
        return {"execute": lambda: ctx.setOffset(ctx.cursor.startOfLogicalLine().offset)}
    result = handleNormalInput(input, 1, ctx)
    return result or {}


def fromCount(state: dict, input: str, ctx: Any) -> dict:
    if input.isdigit():
        new_digits = state["digits"] + input
        count = min(int(new_digits), MAX_VIM_COUNT)
        return {"next": {"type": "count", "digits": str(count)}}
    count = int(state["digits"])
    result = handleNormalInput(input, count, ctx)
    return result or {"next": {"type": "idle"}}


def fromOperator(state: dict, input: str, ctx: Any) -> dict:
    if input == state["op"][0]:
        return {"execute": lambda: executeLineOp(state["op"], state["count"], ctx)}
    if input.isdigit():
        return {"next": {"type": "operatorCount", "op": state["op"], "count": state["count"], "digits": input}}
    result = handleOperatorInput(state["op"], state["count"], input, ctx)
    return result or {"next": {"type": "idle"}}


def fromOperatorCount(state: dict, input: str, ctx: Any) -> dict:
    if input.isdigit():
        new_digits = state["digits"] + input
        parsed = min(int(new_digits), MAX_VIM_COUNT)
        return {"next": {**state, "digits": str(parsed)}}
    motion_count = int(state["digits"])
    effective_count = state["count"] * motion_count
    result = handleOperatorInput(state["op"], effective_count, input, ctx)
    return result or {"next": {"type": "idle"}}


def fromOperatorFind(state: dict, input: str, ctx: Any) -> dict:
    return {"execute": lambda: executeOperatorFind(state["op"], state["find"], input, state["count"], ctx)}


def fromOperatorTextObj(state: dict, input: str, ctx: Any) -> dict:
    if input in TEXT_OBJ_TYPES:
        return {"execute": lambda: executeOperatorTextObj(state["op"], state["scope"], input, state["count"], ctx)}
    return {"next": {"type": "idle"}}


def fromFind(state: dict, input: str, ctx: Any) -> dict:
    def _find() -> None:
        result = ctx.cursor.findCharacter(input, state["find"], state["count"])
        if result is not None:
            ctx.setOffset(result)
            ctx.setLastFind(state["find"], input)
    return {"execute": _find}


def fromG(state: dict, input: str, ctx: Any) -> dict:
    if input in {"j", "k"}:
        return {"execute": lambda: ctx.setOffset(resolveMotion(f"g{input}", ctx.cursor, state["count"]).offset)}
    if input == "g":
        if state["count"] > 1:
            def _goto() -> None:
                lines = ctx.text.split("\n")
                target_line = min(state["count"] - 1, len(lines) - 1)
                offset = 0
                for index in range(target_line):
                    offset += len(lines[index]) + 1
                ctx.setOffset(offset)
            return {"execute": _goto}
        return {"execute": lambda: ctx.setOffset(ctx.cursor.startOfFirstLine().offset)}
    return {"next": {"type": "idle"}}


def fromOperatorG(state: dict, input: str, ctx: Any) -> dict:
    if input in {"j", "k"}:
        return {"execute": lambda: executeOperatorMotion(state["op"], f"g{input}", state["count"], ctx)}
    if input == "g":
        return {"execute": lambda: executeOperatorGg(state["op"], state["count"], ctx)}
    return {"next": {"type": "idle"}}


def fromReplace(state: dict, input: str, ctx: Any) -> dict:
    if input == "":
        return {"next": {"type": "idle"}}
    return {"execute": lambda: executeReplace(input, state["count"], ctx)}


def fromIndent(state: dict, input: str, ctx: Any) -> dict:
    if input == state["dir"]:
        return {"execute": lambda: executeIndent(state["dir"], state["count"], ctx)}
    return {"next": {"type": "idle"}}


def executeRepeatFind(reverse: bool, count: int, ctx: Any) -> None:
    last_find = ctx.getLastFind()
    if not last_find:
        return
    find_type = last_find["type"]
    if reverse:
        flip = {"f": "F", "F": "f", "t": "T", "T": "t"}
        find_type = flip[find_type]
    result = ctx.cursor.findCharacter(last_find["char"], find_type, count)
    if result is not None:
        ctx.setOffset(result)


handle_normal_input = handleNormalInput
handle_operator_input = handleOperatorInput
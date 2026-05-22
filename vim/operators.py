"""Vim operator helpers — mirrors src/vim/operators.ts."""
from __future__ import annotations

from typing import Any, Protocol

from .motions import isInclusiveMotion, isLinewiseMotion, resolveMotion
from .textObjects import findTextObject


class OperatorContext(Protocol):
    cursor: Any
    text: str

    def setText(self, text: str) -> None: ...
    def setOffset(self, offset: int) -> None: ...
    def enterInsert(self, offset: int) -> None: ...
    def getRegister(self) -> str: ...
    def setRegister(self, content: str, linewise: bool) -> None: ...
    def getLastFind(self) -> dict | None: ...
    def setLastFind(self, find_type: str, char: str) -> None: ...
    def recordChange(self, change: dict) -> None: ...


def _first_grapheme(text: str) -> str:
    return text[:1]


def _last_grapheme(text: str) -> str:
    return text[-1:] if text else ""


def _cursor_equals(left: Any, right: Any) -> bool:
    if hasattr(left, "equals"):
        return bool(left.equals(right))
    return getattr(left, "offset", None) == getattr(right, "offset", None)


def _next_offset(cursor: Any, offset: int) -> int:
    measured = getattr(cursor, "measuredText", None)
    if measured is not None and hasattr(measured, "nextOffset"):
        return measured.nextOffset(offset)
    return min(len(getattr(cursor, "text", "")), offset + 1)


def _line_of_offset(text: str, offset: int) -> int:
    return text[:offset].count("\n")


def _line_start_offset(lines: list[str], line_index: int) -> int:
    return sum(len(line) + 1 for line in lines[:line_index]) if line_index > 0 else 0


def executeOperatorMotion(op: str, motion: str, count: int, ctx: OperatorContext) -> None:
    target = resolveMotion(motion, ctx.cursor, count)
    if _cursor_equals(target, ctx.cursor):
        return
    range_info = getOperatorRange(ctx.cursor, target, motion, op, count)
    applyOperator(op, range_info["from"], range_info["to"], ctx, range_info["linewise"])
    ctx.recordChange({"type": "operator", "op": op, "motion": motion, "count": count})


def executeOperatorFind(op: str, findType: str, char: str, count: int, ctx: OperatorContext) -> None:
    target_offset = ctx.cursor.findCharacter(char, findType, count)
    if target_offset is None:
        return
    target = type(ctx.cursor)(ctx.cursor.measuredText, target_offset) if getattr(ctx.cursor, "measuredText", None) is not None else ctx.cursor
    if target is ctx.cursor:
        setattr(target, "offset", target_offset)
    range_info = getOperatorRangeForFind(ctx.cursor, target, findType)
    applyOperator(op, range_info["from"], range_info["to"], ctx)
    ctx.setLastFind(findType, char)
    ctx.recordChange({"type": "operatorFind", "op": op, "find": findType, "char": char, "count": count})


def executeOperatorTextObj(op: str, scope: str, objType: str, count: int, ctx: OperatorContext) -> None:
    range_info = findTextObject(ctx.text, ctx.cursor.offset, objType, scope == "inner")
    if not range_info:
        return
    applyOperator(op, range_info["start"], range_info["end"], ctx)
    ctx.recordChange({"type": "operatorTextObj", "op": op, "objType": objType, "scope": scope, "count": count})


def executeLineOp(op: str, count: int, ctx: OperatorContext) -> None:
    text = ctx.text
    lines = text.split("\n")
    current_line = _line_of_offset(text, ctx.cursor.offset)
    lines_to_affect = min(count, max(0, len(lines) - current_line))
    line_start = ctx.cursor.startOfLogicalLine().offset if hasattr(ctx.cursor, "startOfLogicalLine") else _line_start_offset(lines, current_line)
    line_end = line_start
    for _ in range(lines_to_affect):
        next_newline = text.find("\n", line_end)
        line_end = len(text) if next_newline == -1 else next_newline + 1

    content = text[line_start:line_end]
    if not content.endswith("\n"):
        content += "\n"
    ctx.setRegister(content, True)

    if op == "yank":
        ctx.setOffset(line_start)
    elif op == "delete":
        delete_start = line_start
        delete_end = line_end
        if delete_end == len(text) and delete_start > 0 and text[delete_start - 1] == "\n":
            delete_start -= 1
        new_text = text[:delete_start] + text[delete_end:]
        ctx.setText(new_text)
        max_off = max(0, len(new_text) - (len(_last_grapheme(new_text)) or 1))
        ctx.setOffset(min(delete_start, max_off))
    elif op == "change":
        if len(lines) == 1:
            ctx.setText("")
            ctx.enterInsert(0)
        else:
            before = lines[:current_line]
            after = lines[current_line + lines_to_affect:]
            new_text = "\n".join([*before, "", *after])
            ctx.setText(new_text)
            ctx.enterInsert(line_start)

    ctx.recordChange({"type": "operator", "op": op, "motion": op[0], "count": count})


def executeX(count: int, ctx: OperatorContext) -> None:
    start = ctx.cursor.offset
    if start >= len(ctx.text):
        return
    end_cursor = ctx.cursor
    for _ in range(count):
        if hasattr(end_cursor, "isAtEnd") and end_cursor.isAtEnd():
            break
        end_cursor = end_cursor.right() if hasattr(end_cursor, "right") else end_cursor
        if end_cursor is ctx.cursor:
            break
    end = getattr(end_cursor, "offset", start + count)
    deleted = ctx.text[start:end]
    new_text = ctx.text[:start] + ctx.text[end:]
    ctx.setRegister(deleted, False)
    ctx.setText(new_text)
    max_off = max(0, len(new_text) - (len(_last_grapheme(new_text)) or 1))
    ctx.setOffset(min(start, max_off))
    ctx.recordChange({"type": "x", "count": count})


def executeReplace(char: str, count: int, ctx: OperatorContext) -> None:
    offset = ctx.cursor.offset
    new_text = ctx.text
    for _ in range(count):
        if offset >= len(new_text):
            break
        grapheme_len = len(_first_grapheme(new_text[offset:])) or 1
        new_text = new_text[:offset] + char + new_text[offset + grapheme_len:]
        offset += len(char)
    ctx.setText(new_text)
    ctx.setOffset(max(0, offset - len(char)))
    ctx.recordChange({"type": "replace", "char": char, "count": count})


def executeToggleCase(count: int, ctx: OperatorContext) -> None:
    start = ctx.cursor.offset
    if start >= len(ctx.text):
        return
    new_text = ctx.text
    offset = start
    toggled = 0
    while offset < len(new_text) and toggled < count:
        grapheme = _first_grapheme(new_text[offset:])
        grapheme_len = len(grapheme) or 1
        replacement = grapheme.lower() if grapheme == grapheme.upper() else grapheme.upper()
        new_text = new_text[:offset] + replacement + new_text[offset + grapheme_len:]
        offset += len(replacement)
        toggled += 1
    ctx.setText(new_text)
    ctx.setOffset(offset)
    ctx.recordChange({"type": "toggleCase", "count": count})


def executeJoin(count: int, ctx: OperatorContext) -> None:
    text = ctx.text
    lines = text.split("\n")
    current_line = ctx.cursor.getPosition()["line"] if hasattr(ctx.cursor, "getPosition") else _line_of_offset(text, ctx.cursor.offset)
    if current_line >= len(lines) - 1:
        return
    lines_to_join = min(count, len(lines) - current_line - 1)
    joined_line = lines[current_line]
    cursor_pos = len(joined_line)
    for index in range(1, lines_to_join + 1):
        next_line = (lines[current_line + index] or "").lstrip()
        if next_line:
            if joined_line and not joined_line.endswith(" "):
                joined_line += " "
            joined_line += next_line
    new_lines = [*lines[:current_line], joined_line, *lines[current_line + lines_to_join + 1:]]
    new_text = "\n".join(new_lines)
    ctx.setText(new_text)
    ctx.setOffset(_line_start_offset(new_lines, current_line) + cursor_pos)
    ctx.recordChange({"type": "join", "count": count})


def executePaste(after: bool, count: int, ctx: OperatorContext) -> None:
    register = ctx.getRegister()
    if not register:
        return
    is_linewise = register.endswith("\n")
    content = register[:-1] if is_linewise else register
    if is_linewise:
        lines = ctx.text.split("\n")
        current_line = ctx.cursor.getPosition()["line"] if hasattr(ctx.cursor, "getPosition") else _line_of_offset(ctx.text, ctx.cursor.offset)
        insert_line = current_line + 1 if after else current_line
        content_lines = content.split("\n") if content else [""]
        repeated: list[str] = []
        for _ in range(count):
            repeated.extend(content_lines)
        new_lines = [*lines[:insert_line], *repeated, *lines[insert_line:]]
        new_text = "\n".join(new_lines)
        ctx.setText(new_text)
        ctx.setOffset(_line_start_offset(new_lines, insert_line))
    else:
        text_to_insert = content * count
        insert_point = ctx.cursor.offset
        if after and ctx.cursor.offset < len(ctx.text):
            insert_point = _next_offset(ctx.cursor, ctx.cursor.offset)
        new_text = ctx.text[:insert_point] + text_to_insert + ctx.text[insert_point:]
        last_grapheme = _last_grapheme(text_to_insert)
        new_offset = insert_point + len(text_to_insert) - (len(last_grapheme) or 1)
        ctx.setText(new_text)
        ctx.setOffset(max(insert_point, new_offset))


def executeIndent(dir: str, count: int, ctx: OperatorContext) -> None:
    lines = ctx.text.split("\n")
    current_line = ctx.cursor.getPosition()["line"] if hasattr(ctx.cursor, "getPosition") else _line_of_offset(ctx.text, ctx.cursor.offset)
    lines_to_affect = min(count, len(lines) - current_line)
    indent = "  "
    for index in range(lines_to_affect):
        line_idx = current_line + index
        line = lines[line_idx]
        if dir == ">":
            lines[line_idx] = indent + line
        elif line.startswith(indent):
            lines[line_idx] = line[len(indent):]
        elif line.startswith("\t"):
            lines[line_idx] = line[1:]
        else:
            removed = 0
            pos = 0
            while pos < len(line) and removed < len(indent) and line[pos].isspace():
                removed += 1
                pos += 1
            lines[line_idx] = line[pos:]
    new_text = "\n".join(lines)
    current_line_text = lines[current_line] if current_line < len(lines) else ""
    first_non_blank = len(current_line_text) - len(current_line_text.lstrip())
    ctx.setText(new_text)
    ctx.setOffset(_line_start_offset(lines, current_line) + first_non_blank)
    ctx.recordChange({"type": "indent", "dir": dir, "count": count})


def executeOpenLine(direction: str, ctx: OperatorContext) -> None:
    lines = ctx.text.split("\n")
    current_line = ctx.cursor.getPosition()["line"] if hasattr(ctx.cursor, "getPosition") else _line_of_offset(ctx.text, ctx.cursor.offset)
    insert_line = current_line + 1 if direction == "below" else current_line
    new_lines = [*lines[:insert_line], "", *lines[insert_line:]]
    new_text = "\n".join(new_lines)
    ctx.setText(new_text)
    ctx.enterInsert(_line_start_offset(new_lines, insert_line))
    ctx.recordChange({"type": "openLine", "direction": direction})


def getOperatorRange(cursor: Any, target: Any, motion: str, op: str, count: int) -> dict:
    start = min(cursor.offset, target.offset)
    end = max(cursor.offset, target.offset)
    linewise = False
    if op == "change" and motion in {"w", "W"}:
        word_cursor = cursor
        for _ in range(max(0, count - 1)):
            word_cursor = word_cursor.nextVimWord() if motion == "w" else word_cursor.nextWORD()
        word_end = word_cursor.endOfVimWord() if motion == "w" else word_cursor.endOfWORD()
        end = _next_offset(cursor, word_end.offset)
    elif isLinewiseMotion(motion):
        linewise = True
        text = cursor.text
        next_newline = text.find("\n", end)
        if next_newline == -1:
            end = len(text)
            if start > 0 and text[start - 1] == "\n":
                start -= 1
        else:
            end = next_newline + 1
    elif isInclusiveMotion(motion) and cursor.offset <= target.offset:
        end = _next_offset(cursor, end)
    if hasattr(cursor, "snapOutOfImageRef"):
        start = cursor.snapOutOfImageRef(start, "start")
        end = cursor.snapOutOfImageRef(end, "end")
    return {"from": start, "to": end, "linewise": linewise}


def getOperatorRangeForFind(cursor: Any, target: Any, _findType: str) -> dict:
    start = min(cursor.offset, target.offset)
    max_offset = max(cursor.offset, target.offset)
    end = _next_offset(cursor, max_offset)
    return {"from": start, "to": end}


def applyOperator(op: str, start: int, end: int, ctx: OperatorContext, linewise: bool = False) -> None:
    content = ctx.text[start:end]
    if linewise and not content.endswith("\n"):
        content += "\n"
    ctx.setRegister(content, linewise)
    if op == "yank":
        ctx.setOffset(start)
    elif op == "delete":
        new_text = ctx.text[:start] + ctx.text[end:]
        ctx.setText(new_text)
        max_off = max(0, len(new_text) - (len(_last_grapheme(new_text)) or 1))
        ctx.setOffset(min(start, max_off))
    elif op == "change":
        new_text = ctx.text[:start] + ctx.text[end:]
        ctx.setText(new_text)
        ctx.enterInsert(start)


def executeOperatorG(op: str, count: int, ctx: OperatorContext) -> None:
    target = ctx.cursor.startOfLastLine() if count == 1 else ctx.cursor.goToLine(count)
    if _cursor_equals(target, ctx.cursor):
        return
    range_info = getOperatorRange(ctx.cursor, target, "G", op, count)
    applyOperator(op, range_info["from"], range_info["to"], ctx, range_info["linewise"])
    ctx.recordChange({"type": "operator", "op": op, "motion": "G", "count": count})


def executeOperatorGg(op: str, count: int, ctx: OperatorContext) -> None:
    target = ctx.cursor.startOfFirstLine() if count == 1 else ctx.cursor.goToLine(count)
    if _cursor_equals(target, ctx.cursor):
        return
    range_info = getOperatorRange(ctx.cursor, target, "gg", op, count)
    applyOperator(op, range_info["from"], range_info["to"], ctx, range_info["linewise"])
    ctx.recordChange({"type": "operator", "op": op, "motion": "gg", "count": count})


execute_operator_motion = executeOperatorMotion
execute_operator_find = executeOperatorFind
execute_operator_text_obj = executeOperatorTextObj
execute_line_op = executeLineOp
execute_x = executeX
execute_replace = executeReplace
execute_toggle_case = executeToggleCase
execute_join = executeJoin
execute_paste = executePaste
execute_indent = executeIndent
execute_open_line = executeOpenLine
execute_operator_g = executeOperatorG
execute_operator_gg = executeOperatorGg
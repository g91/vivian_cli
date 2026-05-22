"""Port of src/ink/parse-keypress.ts."""
from __future__ import annotations

import re
from typing import Any

from .termio.tokenize import createTokenizer

META_KEY_CODE_RE = re.compile(r"^(?:\x1b)([a-zA-Z0-9])$")
FN_KEY_RE = re.compile(r"^(?:\x1b+)(O|N|\[|\[\[)(?:(\d+)(?:;(\d+))?([~^$])|(?:1;)?(\d+)?([a-zA-Z]))")
CSI_U_RE = re.compile(r"^\x1b\[(\d+)(?:;(\d+))?u")
MODIFY_OTHER_KEYS_RE = re.compile(r"^\x1b\[27;(\d+);(\d+)~")
DECRPM_RE = re.compile(r"^\x1b\[\?(\d+);(\d+)\$y$")
DA1_RE = re.compile(r"^\x1b\[\?([\d;]*)c$")
DA2_RE = re.compile(r"^\x1b\[>([\d;]*)c$")
KITTY_FLAGS_RE = re.compile(r"^\x1b\[\?(\d+)u$")
CURSOR_POSITION_RE = re.compile(r"^\x1b\[\?(\d+);(\d+)R$")
OSC_RESPONSE_RE = re.compile(r"^\x1b\](\d+);(.*?)(?:\x07|\x1b\\)$", re.DOTALL)
XTVERSION_RE = re.compile(r"^\x1bP>\|(.*?)(?:\x07|\x1b\\)$", re.DOTALL)
SGR_MOUSE_RE = re.compile(r"^\x1b\[<(\d+);(\d+);(\d+)([Mm])$")

KEY_NAME: dict[str, str] = {
    "OP": "f1", "OQ": "f2", "OR": "f3", "OS": "f4",
    "Op": "0", "Oq": "1", "Or": "2", "Os": "3", "Ot": "4", "Ou": "5", "Ov": "6", "Ow": "7", "Ox": "8", "Oy": "9",
    "Oj": "*", "Ok": "+", "Ol": ",", "Om": "-", "On": ".", "Oo": "/", "OM": "return",
    "[11~": "f1", "[12~": "f2", "[13~": "f3", "[14~": "f4",
    "[[A": "f1", "[[B": "f2", "[[C": "f3", "[[D": "f4", "[[E": "f5",
    "[15~": "f5", "[17~": "f6", "[18~": "f7", "[19~": "f8", "[20~": "f9", "[21~": "f10", "[23~": "f11", "[24~": "f12",
    "[A": "up", "[B": "down", "[C": "right", "[D": "left", "[E": "clear", "[F": "end", "[H": "home",
    "OA": "up", "OB": "down", "OC": "right", "OD": "left", "OE": "clear", "OF": "end", "OH": "home",
    "[1~": "home", "[2~": "insert", "[3~": "delete", "[4~": "end", "[5~": "pageup", "[6~": "pagedown",
    "[[5~": "pageup", "[[6~": "pagedown",
    "[7~": "home", "[8~": "end",
    "[a": "up", "[b": "down", "[c": "right", "[d": "left", "[e": "clear",
    "[2$": "insert", "[3$": "delete", "[5$": "pageup", "[6$": "pagedown", "[7$": "home", "[8$": "end",
    "Oa": "up", "Ob": "down", "Oc": "right", "Od": "left", "Oe": "clear",
    "[2^": "insert", "[3^": "delete", "[5^": "pageup", "[6^": "pagedown", "[7^": "home", "[8^": "end",
    "[Z": "tab",
}

NON_ALPHANUMERIC_KEYS = [
    *[v for v in KEY_NAME.values() if len(v) > 1],
    "escape", "backspace", "wheelup", "wheeldown", "mouse",
]

DECRPM_STATUS = {"NOT_RECOGNIZED": 0, "SET": 1, "RESET": 2, "PERMANENTLY_SET": 3, "PERMANENTLY_RESET": 4}

INITIAL_STATE: dict[str, Any] = {"mode": "NORMAL", "incomplete": "", "pasteBuffer": ""}


def _parseTerminalResponse(s: str) -> dict[str, Any] | None:
    if s.startswith("\x1b["):
        m = DECRPM_RE.match(s)
        if m:
            return {"type": "decrpm", "mode": int(m.group(1)), "status": int(m.group(2))}
        m = DA1_RE.match(s)
        if m:
            return {"type": "da1", "params": [int(x) for x in m.group(1).split(";") if x]}
        m = DA2_RE.match(s)
        if m:
            return {"type": "da2", "params": [int(x) for x in m.group(1).split(";") if x]}
        m = KITTY_FLAGS_RE.match(s)
        if m:
            return {"type": "kittyKeyboard", "flags": int(m.group(1))}
        m = CURSOR_POSITION_RE.match(s)
        if m:
            return {"type": "cursorPosition", "row": int(m.group(1)), "col": int(m.group(2))}
    if s.startswith("\x1b]"):
        m = OSC_RESPONSE_RE.match(s)
        if m:
            return {"type": "osc", "code": int(m.group(1)), "data": m.group(2)}
    if s.startswith("\x1bP"):
        m = XTVERSION_RE.match(s)
        if m:
            return {"type": "xtversion", "name": m.group(1)}
    return None


def _parseMouseEvent(s: str) -> dict[str, Any] | None:
    m = SGR_MOUSE_RE.match(s)
    if not m:
        return None
    button = int(m.group(1))
    if button & 0x40:
        return None  # wheel
    return {
        "kind": "mouse",
        "button": button & 0x1F,
        "action": "press" if m.group(4) == "M" else "release",
        "col": int(m.group(2)) - 1,
        "row": int(m.group(3)) - 1,
        "sequence": s,
    }


def _parseKeypress(s: str = "") -> dict[str, Any]:
    if not s:
        return {"kind": "key", "name": "", "ctrl": False, "meta": False, "shift": False,
                "option": False, "super": False, "sequence": "", "raw": "", "isPasted": False}

    # CSI u (kitty)
    m = CSI_U_RE.match(s)
    if m:
        cp = int(m.group(1))
        mod = int(m.group(2)) if m.group(2) else 1
        shift = bool(mod & 2)
        meta = bool(mod & 4)
        ctrl = bool(mod & 8)
        name = chr(cp) if 32 <= cp < 127 else _keycodeToName(cp)
        return {"kind": "key", "name": name, "ctrl": ctrl, "meta": meta, "shift": shift,
                "option": meta, "super": bool(mod & 16), "sequence": s, "raw": s, "isPasted": False}

    # modifyOtherKeys
    m = MODIFY_OTHER_KEYS_RE.match(s)
    if m:
        mod = int(m.group(1))
        kc = int(m.group(2))
        shift = bool(mod & 2)
        meta = bool(mod & 4)
        ctrl = bool(mod & 8)
        name = _keycodeToName(kc)
        return {"kind": "key", "name": name, "ctrl": ctrl, "meta": meta, "shift": shift,
                "option": meta, "super": bool(mod & 16), "sequence": s, "raw": s, "isPasted": False}

    # ESC letter (meta)
    m = META_KEY_CODE_RE.match(s)
    if m:
        return {"kind": "key", "name": m.group(1).lower(), "ctrl": False, "meta": True, "shift": False,
                "option": True, "super": False, "sequence": s, "raw": s, "isPasted": False}

    # Function keys
    m = FN_KEY_RE.match(s)
    if m:
        seq = m.group(0).replace("\x1b", "")
        name = KEY_NAME.get(seq, "")
        return {"kind": "key", "name": name, "ctrl": False, "meta": False, "shift": False,
                "option": False, "super": False, "sequence": s, "raw": s, "isPasted": False}

    # Simple printable
    if len(s) == 1:
        return {"kind": "key", "name": s, "ctrl": False, "meta": False, "shift": False,
                "option": False, "super": False, "sequence": s, "raw": s, "isPasted": False}

    return {"kind": "key", "name": s, "ctrl": False, "meta": False, "shift": False,
            "option": False, "super": False, "sequence": s, "raw": s, "isPasted": False}


def _keycodeToName(kc: int) -> str | None:
    if kc == 13:
        return "return"
    if kc == 27:
        return "escape"
    if kc == 127:
        return "backspace"
    if kc == 9:
        return "tab"
    if 32 <= kc < 127:
        return chr(kc)
    # Function keys
    fn_map = {
        57344: "up", 57345: "down", 57346: "left", 57347: "right",
        57348: "home", 57349: "end", 57350: "pageup", 57351: "pagedown",
        57352: "insert", 57353: "delete",
        57354: "f1", 57355: "f2", 57356: "f3", 57357: "f4",
        57358: "f5", 57359: "f6", 57360: "f7", 57361: "f8",
        57362: "f9", 57363: "f10", 57364: "f11", 57365: "f12",
    }
    return fn_map.get(kc)


def parseMultipleKeypresses(prevState: dict[str, Any], input: str | bytes | None = "") -> tuple[list[dict[str, Any]], dict[str, Any]]:
    isFlush = input is None
    inputStr = "" if isFlush else (input.decode() if isinstance(input, bytes) else input)

    tokenizer = prevState.get("_tokenizer") or createTokenizer(x10Mouse=True)
    tokens = tokenizer.flush() if isFlush else tokenizer.feed(inputStr)

    keys: list[dict[str, Any]] = []
    inPaste = prevState.get("mode") == "IN_PASTE"
    pasteBuffer = prevState.get("pasteBuffer", "")

    for token in tokens:
        if token.type == "sequence":
            seq = token.value
            # Check for bracketed paste
            if seq == "\x1b[200~":
                inPaste = True
                pasteBuffer = ""
                continue
            if seq == "\x1b[201~":
                if inPaste and pasteBuffer:
                    keys.append({"kind": "key", "name": "", "ctrl": False, "meta": False, "shift": False,
                                 "option": False, "super": False, "sequence": pasteBuffer, "raw": pasteBuffer, "isPasted": True})
                inPaste = False
                pasteBuffer = ""
                continue

            if inPaste:
                pasteBuffer += seq
                continue

            # Try terminal response
            resp = _parseTerminalResponse(seq)
            if resp:
                keys.append({"kind": "response", "sequence": seq, "response": resp})
                continue

            # Try mouse
            mouse = _parseMouseEvent(seq)
            if mouse:
                keys.append(mouse)
                continue

            keys.append(_parseKeypress(seq))
        else:
            if inPaste:
                pasteBuffer += token.value
            else:
                for ch in token.value:
                    keys.append(_parseKeypress(ch))

    if isFlush and inPaste and pasteBuffer:
        keys.append({"kind": "key", "name": "", "ctrl": False, "meta": False, "shift": False,
                     "option": False, "super": False, "sequence": pasteBuffer, "raw": pasteBuffer, "isPasted": True})

    newState = {
        "mode": "IN_PASTE" if inPaste else "NORMAL",
        "incomplete": tokenizer.buffer(),
        "pasteBuffer": pasteBuffer,
        "_tokenizer": tokenizer,
    }

    return keys, newState

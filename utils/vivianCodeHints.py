"""Port of src/utils/vivianCodeHints.ts

vivian Code hints protocol — scans shell tool output for <vivian-code-hint />
tags, strips them, and surfaces an install prompt to the user.
"""
from __future__ import annotations
import re
from typing import Any, Callable, Dict, List, Optional, Set

vivianCodeHintType = str  # "plugin"
vivianCodeHint = Dict[str, Any]

SUPPORTED_VERSIONS: Set[int] = {1}
SUPPORTED_TYPES: Set[str] = {"plugin"}

_HINT_TAG_RE = re.compile(r"^[ \t]*<vivian-code-hint\s+([^>]*?)\s*/>[ \t]*$", re.MULTILINE)
_ATTR_RE = re.compile(r"(\w+)=(?:\"([^\"]*)\"|([^\s/>]+))")


def _parse_attrs(tag_body: str) -> Dict[str, str]:
    attrs: Dict[str, str] = {}
    for m in _ATTR_RE.finditer(tag_body):
        attrs[m.group(1)] = m.group(2) if m.group(2) is not None else (m.group(3) or "")
    return attrs


def _first_command_token(command: str) -> str:
    trimmed = command.strip()
    idx = re.search(r"\s", trimmed)
    return trimmed if idx is None else trimmed[:idx.start()]


def extractvivianCodeHints(output: str, command: str) -> Dict[str, Any]:
    """Scan shell tool output for hint tags, returning the parsed hints and
    the output with hint lines removed.
    """
    if "<vivian-code-hint" not in output:
        return {"hints": [], "stripped": output}

    source_command = _first_command_token(command)
    hints: List[vivianCodeHint] = []

    def replace_match(m):
        raw_line = m.group(0)
        attrs = _parse_attrs(raw_line)
        v_str = attrs.get("v")
        v = int(v_str) if v_str and v_str.isdigit() else -1
        hint_type = attrs.get("type")
        value = attrs.get("value")

        if v not in SUPPORTED_VERSIONS:
            return ""
        if not hint_type or hint_type not in SUPPORTED_TYPES:
            return ""
        if not value:
            return ""
        hints.append({"v": v, "type": hint_type, "value": value, "sourceCommand": source_command})
        return ""

    stripped = _HINT_TAG_RE.sub(replace_match, output)
    if hints or stripped != output:
        stripped = re.sub(r"\n{3,}", "\n\n", stripped)
    return {"hints": hints, "stripped": stripped}


parseAttrs = _parse_attrs
firstCommandToken = _first_command_token


# Pending-hint store
_pending_hint: Optional[vivianCodeHint] = None
_shown_this_session: bool = False
_subscribers: List[Callable] = []


def _notify():
    for cb in list(_subscribers):
        try:
            cb()
        except Exception:
            pass


def setPendingHint(hint: vivianCodeHint) -> None:
    global _pending_hint
    if _shown_this_session:
        return
    _pending_hint = hint
    _notify()


def clearPendingHint() -> None:
    global _pending_hint
    if _pending_hint is not None:
        _pending_hint = None
        _notify()


def markShownThisSession() -> None:
    global _shown_this_session
    _shown_this_session = True


def subscribeToPendingHint(cb: Callable) -> Callable:
    _subscribers.append(cb)
    def unsubscribe():
        try:
            _subscribers.remove(cb)
        except ValueError:
            pass
    return unsubscribe


def getPendingHintSnapshot() -> Optional[vivianCodeHint]:
    return _pending_hint


def hasShownHintThisSession() -> bool:
    return _shown_this_session


def _resetvivianCodeHintStore() -> None:
    global _pending_hint, _shown_this_session
    _pending_hint = None
    _shown_this_session = False


_test = {
    "parseAttrs": _parse_attrs,
    "firstCommandToken": _first_command_token,
}

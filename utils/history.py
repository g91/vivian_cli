"""History management — mirrors src/history.ts."""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, AsyncGenerator

from ..bootstrap.state import getProjectRoot, getSessionId
from ..utils.envUtils import get_vivian_config_home_dir

logger = logging.getLogger(__name__)

MAX_HISTORY_ITEMS = 100
MAX_PASTED_CONTENT_LENGTH = 1024
_REFERENCE_PATTERN = re.compile(r"\[(Pasted text|Image|\.\.\.Truncated text) #(\d+)(?: \+\d+ lines)?(\.)*\]")


@dataclass
class TimestampedHistoryEntry:
    display: str
    timestamp: float
    resolve: Any


pendingEntries: list[dict[str, Any]] = []
lastAddedEntry: Optional[dict[str, Any]] = None
skippedTimestamps: set[float] = set()


class HistoryManager:
    """Manages command history with persistence."""

    def __init__(self, history_file: Optional[Path] = None):
        self._entries: list[str] = []
        self._index: int = -1
        self._history_file = history_file or Path.home() / ".vivian" / "history.jsonl"
        self._load()

    def _load(self):
        try:
            if self._history_file.exists():
                lines = self._history_file.read_text().strip().split("\n")
                self._entries = []
                for line in lines[-MAX_HISTORY_ITEMS:]:
                    try:
                        entry = json.loads(line)
                        self._entries.append(entry.get("display", line))
                    except json.JSONDecodeError:
                        self._entries.append(line)
        except Exception as e:
            logger.debug(f"History load error: {e}")

    def _save(self):
        try:
            self._history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._history_file, "a") as f:
                if self._entries:
                    entry = json.dumps({
                        "display": self._entries[-1],
                        "timestamp": __import__("time").time(),
                    })
                    f.write(entry + "\n")
        except Exception as e:
            logger.debug(f"History save error: {e}")

    def add(self, entry: str):
        """Add an entry to history."""
        if entry.strip():
            # Don't add duplicates of the last entry
            if not self._entries or self._entries[-1] != entry:
                self._entries.append(entry)
                if len(self._entries) > MAX_HISTORY_ITEMS:
                    self._entries = self._entries[-MAX_HISTORY_ITEMS:]
                self._save()
        self._index = len(self._entries)

    def prev(self) -> Optional[str]:
        """Get previous history entry."""
        if not self._entries:
            return None
        if self._index > 0:
            self._index -= 1
        return self._entries[self._index]

    def next(self) -> Optional[str]:
        """Get next history entry."""
        if not self._entries:
            return None
        if self._index < len(self._entries) - 1:
            self._index += 1
            return self._entries[self._index]
        self._index = len(self._entries)
        return ""

    def search(self, query: str) -> list[str]:
        """Search history for matching entries."""
        query_lower = query.lower()
        return [
            e for e in reversed(self._entries)
            if query_lower in e.lower()
        ][:20]

    def get_recent(self, n: int = 10) -> list[str]:
        """Get the n most recent entries."""
        return self._entries[-n:]

    def clear(self):
        self._entries.clear()
        self._index = -1


def getPastedTextRefNumLines(text: str) -> int:
    return len(re.findall(r"\r\n|\r|\n", text or ""))


def formatPastedTextRef(id: int, numLines: int) -> str:
    if numLines == 0:
        return f"[Pasted text #{id}]"
    if numLines == 1:
        return f"[Pasted text #{id} +1 line]"
    return f"[Pasted text #{id} +{numLines} lines]"


def formatImageRef(id: int) -> str:
    return f"[Image #{id}]"


def parseReferences(input: str) -> list[dict[str, int | str]]:
    matches: list[dict[str, int | str]] = []
    for match in _REFERENCE_PATTERN.finditer(input or ""):
        ref_id = int(match.group(2) or "0")
        if ref_id <= 0:
            continue
        matches.append(
            {
                "id": ref_id,
                "match": match.group(0),
                "index": match.start(),
            }
        )
    return matches


def expandPastedTextRefs(
    input: str,
    pastedContents: dict[int, Any],
) -> str:
    refs = parseReferences(input)
    expanded = input
    for ref in reversed(refs):
        paste = pastedContents.get(ref["id"])
        if not paste:
            continue
        if isinstance(paste, dict):
            if paste.get("type") != "text":
                continue
            replacement = paste.get("content") or ""
        else:
            replacement = str(paste)
        start = int(ref["index"])
        end = start + len(str(ref["match"]))
        expanded = expanded[:start] + replacement + expanded[end:]
    return expanded


def _default_history_path() -> Path:
    return Path(get_vivian_config_home_dir()) / "history.jsonl"


def _deserialize_log_entry(line: str) -> dict[str, Any]:
    return json.loads(line)


async def makeLogEntryReader() -> AsyncGenerator[dict[str, Any], None]:
    current_session = str(getSessionId())
    for entry in reversed(pendingEntries):
        if entry.get("sessionId") == current_session:
            yield entry

    history_path = _default_history_path()
    if not history_path.exists():
        return
    try:
        lines = history_path.read_text(encoding="utf-8").splitlines()
    except Exception as error:
        logger.debug("History load error: %s", error)
        return
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            entry = _deserialize_log_entry(line)
        except Exception:
            continue
        if entry.get("timestamp") in skippedTimestamps:
            continue
        yield entry


async def makeHistoryReader() -> AsyncGenerator[dict[str, Any], None]:
    async for entry in makeLogEntryReader():
        yield {
            "display": entry.get("display", ""),
            "pastedContents": entry.get("pastedContents", {}),
        }


async def getTimestampedHistory() -> AsyncGenerator[TimestampedHistoryEntry, None]:
    current_project = getProjectRoot()
    seen: set[str] = set()
    async for entry in makeLogEntryReader():
        if entry.get("project") != current_project:
            continue
        display = entry.get("display", "")
        if display in seen:
            continue
        seen.add(display)
        yield TimestampedHistoryEntry(
            display=display,
            timestamp=float(entry.get("timestamp", 0)),
            resolve=lambda entry=entry: {
                "display": entry.get("display", ""),
                "pastedContents": entry.get("pastedContents", {}),
            },
        )


async def getHistory() -> AsyncGenerator[dict[str, Any], None]:
    current_project = getProjectRoot()
    current_session = str(getSessionId())
    other_session_entries: list[dict[str, Any]] = []
    yielded = 0

    async for entry in makeLogEntryReader():
        if entry.get("project") != current_project:
            continue
        if entry.get("sessionId") == current_session:
            yield {"display": entry.get("display", ""), "pastedContents": entry.get("pastedContents", {})}
            yielded += 1
            if yielded >= MAX_HISTORY_ITEMS:
                return
        else:
            other_session_entries.append(entry)

    for entry in other_session_entries[: max(0, MAX_HISTORY_ITEMS - yielded)]:
        yield {"display": entry.get("display", ""), "pastedContents": entry.get("pastedContents", {})}


def _append_history_entry(entry: dict[str, Any]) -> None:
    history_path = _default_history_path()
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def addToHistory(command: dict[str, Any] | str) -> None:
    global lastAddedEntry
    entry = {"display": command, "pastedContents": {}} if isinstance(command, str) else dict(command)
    log_entry = {
        "display": entry.get("display", ""),
        "pastedContents": entry.get("pastedContents", {}),
        "timestamp": time.time(),
        "project": getProjectRoot(),
        "sessionId": str(getSessionId()),
    }
    pendingEntries.append(log_entry)
    lastAddedEntry = log_entry
    try:
        _append_history_entry(log_entry)
    except Exception as error:
        logger.debug("History save error: %s", error)


def clearPendingHistoryEntries() -> None:
    pendingEntries.clear()


def removeLastFromHistory() -> None:
    global lastAddedEntry
    if lastAddedEntry is None:
        return
    skippedTimestamps.add(lastAddedEntry.get("timestamp"))
    if pendingEntries and pendingEntries[-1] is lastAddedEntry:
        pendingEntries.pop()
    lastAddedEntry = None


get_pasted_text_ref_num_lines = getPastedTextRefNumLines
format_pasted_text_ref = formatPastedTextRef
format_image_ref = formatImageRef
parse_references = parseReferences
expand_pasted_text_refs = expandPastedTextRefs
make_log_entry_reader = makeLogEntryReader
make_history_reader = makeHistoryReader
get_timestamped_history = getTimestampedHistory
get_history = getHistory
add_to_history = addToHistory
clear_pending_history_entries = clearPendingHistoryEntries
remove_last_from_history = removeLastFromHistory

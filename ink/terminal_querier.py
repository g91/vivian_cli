"""Port of src/ink/terminal-querier.ts."""
from __future__ import annotations

import asyncio
from typing import Any, Callable

from .termio.csi import csi
from .termio.osc import osc

TerminalResponse = dict[str, Any]
TerminalQuery = dict[str, Any]


def decrqm(mode: int) -> TerminalQuery:
    return {
        "request": csi(f"?{mode}$p"),
        "match": lambda r: r.get("type") == "decrpm" and r.get("mode") == mode,
    }


def da1() -> TerminalQuery:
    return {"request": csi("c"), "match": lambda r: r.get("type") == "da1"}


def da2() -> TerminalQuery:
    return {"request": csi(">c"), "match": lambda r: r.get("type") == "da2"}


def kittyKeyboard() -> TerminalQuery:
    return {"request": csi("?u"), "match": lambda r: r.get("type") == "kittyKeyboard"}


def cursorPosition() -> TerminalQuery:
    return {"request": csi("?6n"), "match": lambda r: r.get("type") == "cursorPosition"}


def oscColor(code: int) -> TerminalQuery:
    return {"request": osc(code, "?"), "match": lambda r: r.get("type") == "osc" and r.get("code") == code}


def xtversion() -> TerminalQuery:
    return {"request": csi(">0q"), "match": lambda r: r.get("type") == "xtversion"}


SENTINEL = csi("c")


class TerminalQuerier:
    __slots__ = ("stdout", "queue")

    def __init__(self, stdout: Any) -> None:
        self.stdout = stdout
        self.queue: list[dict[str, Any]] = []

    def send(self, query: TerminalQuery) -> asyncio.Future:
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self.queue.append({
            "kind": "query",
            "match": query["match"],
            "resolve": lambda r: future.set_result(r),
        })
        self.stdout.write(query["request"])
        self.stdout.flush()
        return future

    def flush(self) -> asyncio.Future:
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self.queue.append({"kind": "sentinel", "resolve": lambda: future.set_result(None)})
        self.stdout.write(SENTINEL)
        self.stdout.flush()
        return future

    def onResponse(self, r: TerminalResponse) -> None:
        for i, p in enumerate(self.queue):
            if p["kind"] == "query" and p["match"](r):
                self.queue.pop(i)
                p["resolve"](r)
                return

        if r.get("type") == "da1":
            for i, p in enumerate(self.queue):
                if p["kind"] == "sentinel":
                    for q in self.queue[:i]:
                        if q["kind"] == "query":
                            q["resolve"](None)
                    self.queue = self.queue[i + 1:]
                    p["resolve"]()
                    return

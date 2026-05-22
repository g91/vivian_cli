"""Engine bridge — exposes the async QueryEngine to sync HTTP handlers.

The engine lives in a private asyncio loop on a background thread, just like
the Qt GUI's EngineWorker. Sync HTTP handlers submit a prompt and drain a
queue.Queue of events suitable for SSE.
"""
from __future__ import annotations
import asyncio
import json
import queue
import threading
from typing import Any, Optional

from ..utils.debug_log import dlog as _dlog
from ..gui.chat_modes import compose_mode_prompt

_SENTINEL_DONE = {"__done__": True}


def _serialize_event(event: Any) -> Optional[dict]:
    """Turn a QueryEngine event into a JSON-safe dict for the browser."""
    # Stream chunk (OpenAI delta shape)
    if hasattr(event, "choices"):
        deltas = []
        for choice in getattr(event, "choices", []):
            d = choice.get("delta", {})
            content = d.get("content") or ""
            if content:
                deltas.append(content)
        if deltas:
            return {"type": "chunk", "text": "".join(deltas)}
        return None
    if isinstance(event, dict):
        etype = event.get("type")
        _dlog("bridge: serialize dict type=%r", etype)
        if etype == "tool_call_start":
            return {"type": "tool_start", "name": event.get("name", "?")}
        if etype == "tool_call_args":
            return {"type": "tool_args", "name": event.get("name", "?"),
                    "args": event.get("args") or {}}
        if etype == "tool_result":
            return {
                "type": "tool",
                "name": event.get("tool_name", "?"),
                "result": event.get("result") or {},
            }
        if "choices" in event:
            text = ""
            for choice in event.get("choices", []):
                d = choice.get("delta", {})
                if d.get("content"):
                    text += d["content"]
            if text:
                return {"type": "chunk", "text": text}
            return None
        _dlog("bridge: unhandled dict type=%r — dropping", etype)
        return None
    role = getattr(event, "role", None)
    content = getattr(event, "content", None)
    if role == "system" and content:
        return {"type": "system", "text": str(content)}
    _dlog("bridge: unhandled event type=%s role=%r", type(event).__name__, role)
    return None


class EngineBridge:
    def __init__(self, engine):
        self.engine = engine
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="EngineBridge")
        self._thread.start()
        self._ready.wait(timeout=2.0)

    def _run(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._ready.set()
        self.loop.run_forever()

    def submit(
        self,
        prompt: str,
        *,
        mode_id: str | None = None,
        is_employee: bool = False,
        expose_internal_modes: bool = False,
    ) -> "queue.Queue[dict]":
        """Return a queue of event dicts. A {'__done__': True} sentinel is the
        terminal value."""
        q: queue.Queue[dict] = queue.Queue()
        loop = self.loop
        if loop is None:
            q.put({"type": "error", "error": "engine loop not ready"})
            q.put(_SENTINEL_DONE)
            return q

        async def _consume() -> None:
            effective_prompt = compose_mode_prompt(
                prompt,
                mode_id,
                is_employee=is_employee,
                expose_internal_modes=expose_internal_modes,
            )
            _dlog("bridge: _consume START prompt=%r", effective_prompt[:80])
            try:
                async for event in self.engine.submit_message(effective_prompt):
                    payload = _serialize_event(event)
                    if payload is not None:
                        _dlog("bridge: queuing payload type=%r", payload.get("type"))
                        q.put(payload)
            except Exception as e:
                _dlog("bridge: _consume EXCEPTION %s: %s", type(e).__name__, e)
                q.put({"type": "error", "error": f"{type(e).__name__}: {e}"})
            finally:
                _dlog("bridge: _consume DONE")
                q.put(_SENTINEL_DONE)

        asyncio.run_coroutine_threadsafe(_consume(), loop)
        return q

    def interrupt(self) -> None:
        try:
            self.engine.interrupt()
        except Exception:
            pass


def sse_frame(payload: dict) -> bytes:
    """Format a single SSE 'data:' frame from a JSON-serializable payload."""
    return ("data: " + json.dumps(payload, ensure_ascii=False) + "\n\n").encode("utf-8")


SENTINEL_DONE = _SENTINEL_DONE

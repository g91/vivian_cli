"""Port of src/bridge/replBridgeTransport.ts.

Transport abstraction for replBridge covering v1 (HybridTransport/WebSocket)
and v2 (SSETransport + CCR-style HTTP worker endpoints) transport variants.
"""
from __future__ import annotations

import asyncio
import json
import random
import uuid as _uuid
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse, urlunparse

import httpx

from ..cli.transports.sse_transport import SSEFrame, SSETransport


class ReplBridgeTransport:
    """Abstract transport interface for replBridge."""

    async def write(self, message: Dict[str, Any]) -> None:
        raise NotImplementedError

    async def writeBatch(self, messages: list) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def isConnectedStatus(self) -> bool:
        raise NotImplementedError

    def getStateLabel(self) -> str:
        raise NotImplementedError

    def setOnData(self, callback: Callable[[str], None]) -> None:
        raise NotImplementedError

    def setOnClose(self, callback: Callable[[Optional[int]], None]) -> None:
        raise NotImplementedError

    def setOnConnect(self, callback: Callable[[], None]) -> None:
        raise NotImplementedError

    def connect(self) -> None:
        raise NotImplementedError

    def getLastSequenceNum(self) -> int:
        raise NotImplementedError

    @property
    def droppedBatchCount(self) -> int:
        return 0

    def reportState(self, state: Any) -> None:
        pass

    def reportMetadata(self, metadata: Dict[str, Any]) -> None:
        pass

    def reportDelivery(self, event_id: str, status: str) -> None:
        pass

    async def flush(self) -> None:
        pass


class V1ReplTransport(ReplBridgeTransport):
    """v1 adapter wrapping a HybridTransport-like object."""

    def __init__(self, hybrid: Any) -> None:
        self._hybrid = hybrid

    async def write(self, message: Dict[str, Any]) -> None:
        result = self._hybrid.write(message)
        if asyncio.iscoroutine(result):
            await result

    async def writeBatch(self, messages: list) -> None:
        result = self._hybrid.writeBatch(messages)
        if asyncio.iscoroutine(result):
            await result

    def close(self) -> None:
        self._hybrid.close()

    def isConnectedStatus(self) -> bool:
        return self._hybrid.isConnectedStatus()

    def getStateLabel(self) -> str:
        return self._hybrid.getStateLabel()

    def setOnData(self, callback: Callable[[str], None]) -> None:
        self._hybrid.setOnData(callback)

    def setOnClose(self, callback: Callable[[Optional[int]], None]) -> None:
        self._hybrid.setOnClose(callback)

    def setOnConnect(self, callback: Callable[[], None]) -> None:
        self._hybrid.setOnConnect(callback)

    def connect(self) -> None:
        result = self._hybrid.connect()
        if asyncio.iscoroutine(result):
            asyncio.ensure_future(result)

    def getLastSequenceNum(self) -> int:
        # v1 Session-Ingress WS doesn't use SSE sequence numbers
        return 0

    @property
    def droppedBatchCount(self) -> int:
        return getattr(self._hybrid, "droppedBatchCount", 0)

    def reportState(self, state: Any) -> None:
        pass

    def reportMetadata(self, metadata: Dict[str, Any]) -> None:
        pass

    def reportDelivery(self, event_id: str, status: str) -> None:
        pass

    async def flush(self) -> None:
        pass


def createV1ReplTransport(hybrid: Any) -> V1ReplTransport:
    """Create a v1 ReplBridgeTransport wrapping a HybridTransport."""
    return V1ReplTransport(hybrid)


class V2ReplTransport(ReplBridgeTransport):
    """v2 adapter wrapping SSETransport (reads) + CCRClient (writes)."""

    def __init__(
        self,
        sse: Any,
        ccr: Any,
        epoch: int,
        outbound_only: bool = False,
    ) -> None:
        self._sse = sse
        self._ccr = ccr
        self._epoch = epoch
        self._outbound_only = outbound_only
        self._ccr_initialized = False
        self._closed = False
        self._on_connect_cb: Optional[Callable[[], None]] = None
        self._on_close_cb: Optional[Callable[[Optional[int]], None]] = None

    async def write(self, message: Dict[str, Any]) -> None:
        result = self._ccr.writeEvent(message)
        if asyncio.iscoroutine(result):
            await result

    async def writeBatch(self, messages: list) -> None:
        for m in messages:
            if self._closed:
                break
            result = self._ccr.writeEvent(m)
            if asyncio.iscoroutine(result):
                await result

    def close(self) -> None:
        self._closed = True
        self._ccr.close()
        self._sse.close()

    def isConnectedStatus(self) -> bool:
        return self._ccr_initialized

    def getStateLabel(self) -> str:
        if getattr(self._sse, "isClosedStatus", lambda: False)():
            return "closed"
        if getattr(self._sse, "isConnectedStatus", lambda: False)():
            return "connected" if self._ccr_initialized else "init"
        return "connecting"

    def setOnData(self, callback: Callable[[str], None]) -> None:
        self._sse.setOnData(callback)

    def setOnClose(self, callback: Callable[[Optional[int]], None]) -> None:
        self._on_close_cb = callback
        def _sse_close_handler(code: Optional[int]) -> None:
            self._ccr.close()
            callback(code if code is not None else 4092)
        self._sse.setOnClose(_sse_close_handler)

    def setOnConnect(self, callback: Callable[[], None]) -> None:
        self._on_connect_cb = callback

    def connect(self) -> None:
        if not self._outbound_only:
            asyncio.ensure_future(self._connect_sse())
        asyncio.ensure_future(self._initialize_ccr())

    async def _connect_sse(self) -> None:
        try:
            result = self._sse.connect()
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            pass

    async def _initialize_ccr(self) -> None:
        try:
            from ..utils.debug import log_for_debugging
        except Exception:
            log_for_debugging = lambda msg, **kw: None  # noqa: E731

        try:
            result = self._ccr.initialize(self._epoch)
            if asyncio.iscoroutine(result):
                await result
            self._ccr_initialized = True
            log_for_debugging(
                f"[bridge:repl] v2 transport ready for writes (epoch={self._epoch})"
            )
            if self._on_connect_cb:
                self._on_connect_cb()
        except Exception as err:
            log_for_debugging(
                f"[bridge:repl] CCR v2 initialize failed: {err}",
                level="error",
            )
            self._ccr.close()
            self._sse.close()
            if self._on_close_cb:
                self._on_close_cb(4091)

    def getLastSequenceNum(self) -> int:
        return getattr(self._sse, "getLastSequenceNum", lambda: 0)()

    @property
    def droppedBatchCount(self) -> int:
        return 0

    def reportState(self, state: Any) -> None:
        self._ccr.reportState(state)

    def reportMetadata(self, metadata: Dict[str, Any]) -> None:
        self._ccr.reportMetadata(metadata)

    def reportDelivery(self, event_id: str, status: str) -> None:
        self._ccr.reportDelivery(event_id, status)

    async def flush(self) -> None:
        result = self._ccr.flush()
        if asyncio.iscoroutine(result):
            await result


async def createV2ReplTransport(
    session_url: str,
    ingress_token: str,
    session_id: str,
    initial_sequence_num: Optional[int] = None,
    epoch: Optional[int] = None,
    heartbeat_interval_ms: Optional[int] = None,
    heartbeat_jitter_fraction: Optional[float] = None,
    outbound_only: bool = False,
    get_auth_token: Optional[Callable[[], Optional[str]]] = None,
) -> V2ReplTransport:
    """Create a v2 ReplBridgeTransport (SSETransport + CCRClient)."""
    try:
        from ..utils.debug import log_for_debugging
    except Exception:
        def log_for_debugging(msg, **kw): pass  # noqa: E731

    if get_auth_token:
        def get_auth_headers() -> Dict[str, str]:
            token = get_auth_token()
            return {"Authorization": f"Bearer {token}"} if token else {}
    else:
        try:
            from ..utils.session_ingress_auth import update_session_ingress_auth_token
            update_session_ingress_auth_token(ingress_token)
        except Exception:
            pass
        get_auth_headers = None

    if epoch is None:
        from .workSecret import registerWorker
        epoch = await registerWorker(session_url, ingress_token)

    log_for_debugging(
        f"[bridge:repl] CCR v2: worker sessionId={session_id} epoch={epoch}"
    )

    sse = _SSETransportAdapter(
        session_url=session_url,
        session_id=session_id,
        initial_sequence_num=initial_sequence_num,
        get_auth_headers=get_auth_headers,
    )
    ccr = _MinimalCCRClient(
        sse=sse,
        session_url=session_url,
        get_auth_headers=get_auth_headers,
        heartbeat_interval_ms=heartbeat_interval_ms,
        heartbeat_jitter_fraction=heartbeat_jitter_fraction,
    )

    transport = V2ReplTransport(sse, ccr, epoch, outbound_only)
    return transport


class _SSETransportAdapter:
    """Compatibility adapter exposing the TS-style SSE transport surface."""

    def __init__(
        self,
        session_url: str,
        session_id: str,
        initial_sequence_num: Optional[int],
        get_auth_headers: Optional[Callable[[], Dict[str, str]]],
    ) -> None:
        parsed = urlparse(session_url)
        path = parsed.path.rstrip("/") + "/worker/events/stream"
        sse_url = urlunparse(parsed._replace(path=path))
        self._transport = SSETransport(
            sse_url,
            headers=(get_auth_headers() if get_auth_headers else {}),
            session_id=session_id,
            refresh_headers=get_auth_headers,
        )
        self._last_seq = initial_sequence_num or 0
        self._closed = False
        self._connected = False
        self._on_data: Optional[Callable[[str], None]] = None
        self._on_close: Optional[Callable[[Optional[int]], None]] = None
        self._on_event: Optional[Callable[[Any], None]] = None

    def setOnData(self, cb: Callable[[str], None]) -> None:
        self._on_data = cb

    def setOnClose(self, cb: Callable[[Optional[int]], None]) -> None:
        self._on_close = cb

    def setOnEvent(self, cb: Callable[[Any], None]) -> None:
        self._on_event = cb

    def isClosedStatus(self) -> bool:
        return self._closed

    def isConnectedStatus(self) -> bool:
        return self._connected and not self._closed

    def getLastSequenceNum(self) -> int:
        return self._last_seq

    def close(self) -> None:
        self._closed = True
        result = self._transport.close()
        if asyncio.iscoroutine(result):
            asyncio.ensure_future(result)

    async def connect(self) -> None:
        self._connected = True
        self._transport.set_on_data(self._handle_data)
        self._transport.set_on_close(self._handle_close)
        await self._transport.connect()

    def _handle_data(self, data: str) -> None:
        try:
            parsed = json.loads(data)
        except Exception:
            parsed = None
        if isinstance(parsed, dict):
            event_id = parsed.get("event_id") or parsed.get("id")
            if isinstance(event_id, str):
                try:
                    numeric = int(event_id)
                except ValueError:
                    numeric = self._last_seq + 1
                self._last_seq = max(self._last_seq, numeric)
                if self._on_event:
                    self._on_event(type("StreamEvent", (), {"event_id": event_id})())
        if self._on_data:
            self._on_data(data)

    def _handle_close(self, code: Optional[int]) -> None:
        self._closed = True
        if self._on_close:
            self._on_close(code)


class _MinimalCCRClient:
    """Small CCR v2 client for the REPL bridge path.

    This implements the subset required by replBridgeTransport and
    remoteBridgeCore: initialize, event writes, worker state updates,
    delivery acks, heartbeat, and flush/close.
    """

    def __init__(
        self,
        sse: _SSETransportAdapter,
        session_url: str,
        get_auth_headers: Optional[Callable[[], Dict[str, str]]],
        heartbeat_interval_ms: Optional[int] = None,
        heartbeat_jitter_fraction: Optional[float] = None,
    ) -> None:
        self._sse = sse
        self._session_url = session_url.rstrip("/")
        self._get_auth_headers = get_auth_headers or (lambda: {})
        self._worker_epoch = 0
        self._closed = False
        self._heartbeat_task: Optional[asyncio.Task[Any]] = None
        self._heartbeat_interval_ms = heartbeat_interval_ms or 20_000
        self._heartbeat_jitter_fraction = heartbeat_jitter_fraction or 0.0
        self._current_state: Optional[str] = None

        self._sse.setOnEvent(
            lambda event: self.reportDelivery(getattr(event, "event_id", ""), "received")
            if getattr(event, "event_id", "")
            else None
        )

    async def initialize(self, epoch: int) -> None:
        self._worker_epoch = epoch
        ok = await self._request(
            "put",
            "/worker",
            {
                "worker_status": "idle",
                "worker_epoch": self._worker_epoch,
                "external_metadata": {
                    "pending_action": None,
                    "task_summary": None,
                },
            },
            timeout=10.0,
        )
        if not ok:
            raise RuntimeError("worker initialization failed")
        self._current_state = "idle"
        self._start_heartbeat()

    async def writeEvent(self, msg: Any) -> None:
        payload = dict(msg) if isinstance(msg, dict) else {"payload": msg}
        payload.setdefault("uuid", str(_uuid.uuid4()))
        await self._request(
            "post",
            "/worker/events",
            {"worker_epoch": self._worker_epoch, "events": [{"payload": payload}]},
            timeout=10.0,
            raise_on_failure=True,
        )

    def close(self) -> None:
        self._closed = True
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

    def reportState(self, state: Any) -> None:
        if state == self._current_state:
            return
        self._current_state = str(state)
        asyncio.ensure_future(
            self._request(
                "put",
                "/worker",
                {"worker_epoch": self._worker_epoch, "worker_status": self._current_state},
                timeout=5.0,
            )
        )

    def reportMetadata(self, metadata: Any) -> None:
        asyncio.ensure_future(
            self._request(
                "put",
                "/worker",
                {
                    "worker_epoch": self._worker_epoch,
                    "external_metadata": metadata if isinstance(metadata, dict) else {},
                },
                timeout=5.0,
            )
        )

    def reportDelivery(self, event_id: str, status: str) -> None:
        if not event_id:
            return
        asyncio.ensure_future(
            self._request(
                "post",
                "/worker/events/delivery",
                {
                    "worker_epoch": self._worker_epoch,
                    "events": [{"event_id": event_id, "status": status}],
                },
                timeout=5.0,
            )
        )

    async def flush(self) -> None:
        return None

    async def _request(
        self,
        method: str,
        path: str,
        body: Dict[str, Any],
        *,
        timeout: float,
        raise_on_failure: bool = False,
    ) -> bool:
        headers = self._get_auth_headers()
        if not headers:
            return False
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method.upper(),
                    f"{self._session_url}{path}",
                    json=body,
                    headers={
                        **headers,
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01",
                    },
                )
        except Exception:
            if raise_on_failure:
                raise
            return False

        if 200 <= response.status_code < 300:
            return True
        if response.status_code == 409:
            raise RuntimeError("epoch superseded")
        if response.status_code in (401, 403) and raise_on_failure:
            raise RuntimeError(f"auth failed: {response.status_code}")
        if raise_on_failure:
            raise RuntimeError(f"request failed: {response.status_code}")
        return False

    def _start_heartbeat(self) -> None:
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self) -> None:
        while not self._closed:
            jitter = self._heartbeat_interval_ms * self._heartbeat_jitter_fraction * (2 * random.random() - 1)
            delay_ms = max(1000, self._heartbeat_interval_ms + jitter)
            await asyncio.sleep(delay_ms / 1000.0)
            if self._closed:
                return
            try:
                await self._request(
                    "post",
                    "/worker/heartbeat",
                    {"session_id": self._session_url.rsplit("/", 1)[-1], "worker_epoch": self._worker_epoch},
                    timeout=5.0,
                )
            except Exception:
                return

"""Voice stream STT service — mirrors src/services/voiceStreamSTT.ts."""
from __future__ import annotations

import asyncio
import contextlib
import importlib
import json
import os
from typing import Any, Callable, Optional
from urllib.parse import urlencode

VOICE_STREAM_PATH = "/api/ws/speech_to_text/voice_stream"
KEEPALIVE_INTERVAL_MS = 8_000
KEEPALIVE_MSG = '{"type":"KeepAlive"}'
CLOSE_STREAM_MSG = '{"type":"CloseStream"}'

FINALIZE_TIMEOUTS_MS = {
    "safety": 5_000,
    "noData": 1_500,
}


class VoiceStreamCallbacks:
    def __init__(
        self,
        on_transcript: Callable[[str, bool], None],
        on_error: Callable[[str], None],
        on_close: Callable[[], None],
        on_ready: Callable[["VoiceStreamConnection"], None],
    ) -> None:
        self.on_transcript = on_transcript
        self.on_error = on_error
        self.on_close = on_close
        self.on_ready = on_ready


class VoiceStreamConnection:
    """WebSocket connection to Anthropic's voice_stream STT endpoint.

    Mirrors VoiceStreamConnection from voiceStreamSTT.ts.
    """

    def __init__(self, ws: Any, callbacks: VoiceStreamCallbacks) -> None:
        self._ws: Optional[Any] = ws
        self._callbacks = callbacks
        self._keepalive_task: Optional[asyncio.Task] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._connected = True
        self._finalized = False
        self._finalize_future: Optional[asyncio.Future[str]] = None
        self._last_transcript = ""
        self._endpoint_received = False

    def _resolve_finalize(self, source: str) -> None:
        future = self._finalize_future
        if future is not None and not future.done():
            future.set_result(source)

    async def send_audio(self, data: bytes) -> None:
        """Send a binary audio frame."""
        if self._ws is None or self._finalized:
            return
        await self._ws.send(data)

    async def send(self, audio_chunk: bytes) -> None:
        await self.send_audio(audio_chunk)

    async def finalize(self) -> Optional[str]:
        """Send CloseStream and wait for final transcript."""
        if self._ws is None:
            return "ws_already_closed"
        if self._finalize_future is not None:
            return await self._finalize_future

        loop = asyncio.get_running_loop()
        self._finalize_future = loop.create_future()
        self._finalized = True
        if self._endpoint_received:
            self._resolve_finalize("post_closestream_endpoint")
            return await self._finalize_future
        await self._ws.send(CLOSE_STREAM_MSG)

        async def _safety_timeout() -> None:
            await asyncio.sleep(FINALIZE_TIMEOUTS_MS["safety"] / 1000)
            self._resolve_finalize("safety_timeout")

        async def _no_data_timeout() -> None:
            await asyncio.sleep(FINALIZE_TIMEOUTS_MS["noData"] / 1000)
            self._resolve_finalize("no_data_timeout")

        asyncio.create_task(_safety_timeout())
        asyncio.create_task(_no_data_timeout())
        return await self._finalize_future

    async def close(self) -> None:
        """Close the connection."""
        if self._keepalive_task:
            self._keepalive_task.cancel()
            self._keepalive_task = None
        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None
        self._connected = False
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    def isConnected(self) -> bool:
        return self._connected and self._ws is not None

    async def _keepalive_loop(self) -> None:
        try:
            while self._ws is not None and self._connected:
                await asyncio.sleep(KEEPALIVE_INTERVAL_MS / 1000)
                if self._ws is not None and self._connected:
                    await self._ws.send(KEEPALIVE_MSG)
        except asyncio.CancelledError:
            return

    async def _reader_loop(self) -> None:
        try:
            async for raw in self._ws:
                text = raw.decode() if isinstance(raw, (bytes, bytearray)) else str(raw)
                try:
                    payload = json.loads(text)
                except Exception:
                    continue
                message_type = payload.get("type")
                if message_type == "TranscriptText":
                    self._last_transcript = str(payload.get("data", ""))
                    self._callbacks.on_transcript(self._last_transcript, False)
                elif message_type == "TranscriptEndpoint":
                    self._endpoint_received = True
                    if self._last_transcript:
                        self._callbacks.on_transcript(self._last_transcript, True)
                        self._last_transcript = ""
                    self._resolve_finalize("post_closestream_endpoint")
                elif message_type in ("TranscriptError", "error"):
                    self._callbacks.on_error(str(payload.get("description") or payload.get("message") or "voice_stream error"))
        except asyncio.CancelledError:
            return
        except Exception as exc:
            self._callbacks.on_error(str(exc))
        finally:
            self._connected = False
            self._resolve_finalize("ws_close")
            self._callbacks.on_close()


def isVoiceStreamAvailable() -> bool:
    try:
        from ..utils.auth import is_vivian_ai_subscriber, get_vivian_ai_oauth_tokens

        tokens = get_vivian_ai_oauth_tokens()
        return bool(is_vivian_ai_subscriber() and tokens and getattr(tokens, "access_token", None))
    except Exception:
        return False


async def connectVoiceStream(
    callbacks: VoiceStreamCallbacks,
    options: Optional[dict] = None,
) -> Optional[VoiceStreamConnection]:
    """Create a WebSocket connection to the voice_stream endpoint.

    Mirrors createVoiceStreamConnection() from voiceStreamSTT.ts.
    """
    try:
        websockets = importlib.import_module("websockets")
    except ImportError:
        callbacks.on_error("websockets package is not installed")
        return None

    try:
        from ..utils.auth import check_and_refresh_oauth_token_if_needed, get_vivian_ai_oauth_tokens
        from ..utils.debug import logForDebugging
    except Exception:
        callbacks.on_error("voice auth helpers unavailable")
        return None

    await check_and_refresh_oauth_token_if_needed()
    tokens = get_vivian_ai_oauth_tokens()
    access_token = getattr(tokens, "access_token", None) if tokens is not None else None
    if not access_token:
        logForDebugging("[voice_stream] No OAuth token available")
        return None

    base_url = (
        os.environ.get("VOICE_STREAM_BASE_URL")
        or os.environ.get("ANTHROPIC_BASE_URL")
        or "https://api.anthropic.com"
    )
    ws_base = base_url.replace("https://", "wss://").replace("http://", "ws://")
    query = {
        "encoding": "linear16",
        "sample_rate": "16000",
        "channels": "1",
        "endpointing_ms": "300",
        "utterance_end_ms": "1000",
        "language": (options or {}).get("language", "en"),
    }
    keyterms = (options or {}).get("keyterms") or []
    params = urlencode(list(query.items()) + [("keyterms", term) for term in keyterms])
    url = f"{ws_base}{VOICE_STREAM_PATH}?{params}"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "vivian-cli-python",
        "x-app": "cli",
    }

    ws = await websockets.connect(url, additional_headers=headers, ping_interval=None)
    conn = VoiceStreamConnection(ws, callbacks)
    conn._keepalive_task = asyncio.create_task(conn._keepalive_loop())
    conn._reader_task = asyncio.create_task(conn._reader_loop())
    callbacks.on_ready(conn)
    return conn


async def createVoiceStreamConnection(
    callbacks: VoiceStreamCallbacks,
    base_url: Optional[str] = None,
) -> VoiceStreamConnection:
    conn = await connectVoiceStream(callbacks, {"base_url": base_url} if base_url else None)
    if conn is None:
        raise RuntimeError("Unable to establish voice stream connection")
    return conn


create_voice_stream_connection = createVoiceStreamConnection
connect_voice_stream = connectVoiceStream
is_voice_stream_available = isVoiceStreamAvailable

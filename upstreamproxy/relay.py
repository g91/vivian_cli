"""CCR CONNECT-over-WebSocket relay — mirrors src/upstreamproxy/relay.ts.

Listens on localhost TCP, accepts HTTP CONNECT, tunnels bytes via WebSocket
to the CCR upstreamproxy endpoint using a protobuf-framed message format.
"""
from __future__ import annotations

import asyncio
import struct
import logging
from typing import Callable, Optional

log = logging.getLogger(__name__)

MAX_CHUNK_BYTES = 512 * 1024
PING_INTERVAL_S = 30


def encode_chunk(data: bytes) -> bytes:
    """Encode bytes as an UpstreamProxyChunk protobuf message.

    For `message UpstreamProxyChunk { bytes data = 1; }` the wire format is:
        tag = (1 << 3) | 2 = 0x0a
        varint(length)
        data bytes
    """
    tag = 0x0A
    n = len(data)
    varint: list[int] = []
    while n > 0x7F:
        varint.append((n & 0x7F) | 0x80)
        n >>= 7
    varint.append(n)
    return bytes([tag, *varint]) + data


def decode_chunk(data: bytes) -> Optional[bytes]:
    """Decode the first UpstreamProxyChunk from *data*. Returns the inner bytes."""
    if len(data) < 2:
        return None
    if data[0] != 0x0A:
        return None
    # Read varint length
    pos = 1
    length = 0
    shift = 0
    while pos < len(data):
        b = data[pos]
        pos += 1
        length |= (b & 0x7F) << shift
        shift += 7
        if not (b & 0x80):
            break
    else:
        return None
    return data[pos: pos + length]


class UpstreamRelay:
    """Local TCP → WebSocket relay for CCR upstreamproxy."""

    def __init__(self, ws_url: str, auth_token: str) -> None:
        self._ws_url = ws_url
        self._auth_token = auth_token
        self._server: Optional[asyncio.AbstractServer] = None
        self._port: Optional[int] = None

    @property
    def port(self) -> Optional[int]:
        return self._port

    async def start(self, host: str = "127.0.0.1", port: int = 0) -> int:
        """Start listening. Returns the bound port."""
        self._server = await asyncio.start_server(
            self._handle_client, host, port
        )
        addrs = self._server.sockets or []
        if addrs:
            self._port = addrs[0].getsockname()[1]
        log.debug("Upstream relay listening on port %s", self._port)
        return self._port or 0

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle one CONNECT client."""
        try:
            # Read CONNECT line
            line = await reader.readline()
            if not line.upper().startswith(b"CONNECT "):
                writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                await writer.drain()
                return
            # Drain headers
            while True:
                hdr = await reader.readline()
                if hdr in (b"\r\n", b"\n", b""):
                    break
            # Acknowledge
            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()
            await self._tunnel(reader, writer)
        except Exception as exc:
            log.debug("Relay client error: %s", exc)
        finally:
            writer.close()

    async def _tunnel(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Tunnel bytes between TCP client and WebSocket."""
        try:
            import websockets  # type: ignore

            extra_headers = {"Authorization": f"Bearer {self._auth_token}"}
            async with websockets.connect(
                self._ws_url,
                additional_headers=extra_headers,
                ping_interval=PING_INTERVAL_S,
                max_size=MAX_CHUNK_BYTES * 2,
            ) as ws:
                async def tcp_to_ws() -> None:
                    while True:
                        chunk = await reader.read(MAX_CHUNK_BYTES)
                        if not chunk:
                            break
                        await ws.send(encode_chunk(chunk))

                async def ws_to_tcp() -> None:
                    async for msg in ws:
                        raw = msg if isinstance(msg, bytes) else msg.encode()
                        inner = decode_chunk(raw)
                        if inner:
                            writer.write(inner)
                            await writer.drain()

                done, pending = await asyncio.wait(
                    [
                        asyncio.ensure_future(tcp_to_ws()),
                        asyncio.ensure_future(ws_to_tcp()),
                    ],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()
        except ImportError:
            log.warning("websockets package not available — upstream relay disabled")
        except Exception as exc:
            log.debug("Tunnel error: %s", exc)


async def start_upstream_proxy_relay(
    ws_url: str,
    auth_token: str,
    host: str = "127.0.0.1",
) -> UpstreamRelay:
    """Create and start the relay, returning the instance."""
    relay = UpstreamRelay(ws_url, auth_token)
    await relay.start(host)
    return relay

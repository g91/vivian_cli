"""Port of src/utils/vivianInChrome/chromeNativeHost.ts."""
from __future__ import annotations

import asyncio
import json
import os
import socket
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..debug import logForDebugging
from .common import getSecureSocketPath, getSocketDir

VERSION = "1.0.0"
MAX_MESSAGE_SIZE = 1024 * 1024  # 1MB

_LOG_FILE = (
    str(Path.home() / ".vivian" / "debug" / "chrome-native-host.txt")
    if os.environ.get("USER_TYPE") == "ant"
    else None
)


def _log(message: str, *args: Any) -> None:
    if _LOG_FILE:
        timestamp = datetime.now(timezone.utc).isoformat()
        formatted_args = " " + json.dumps(args) if args else ""
        log_line = f"[{timestamp}] [vivian Chrome Native Host] {message}{formatted_args}\n"
        try:
            Path(_LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
            with open(_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception:
            pass
    logForDebugging(f"[vivian Chrome Native Host] {message}", *args)


def sendChromeMessage(message: str) -> None:
    json_bytes = message.encode("utf-8")
    length_buffer = struct.pack("<I", len(json_bytes))
    sys.stdout.buffer.write(length_buffer)
    sys.stdout.buffer.write(json_bytes)
    sys.stdout.buffer.flush()


class ChromeNativeHost:
    def __init__(self) -> None:
        self._mcp_clients: dict[int, dict[str, Any]] = {}
        self._next_client_id = 1
        self._server: asyncio.AbstractServer | None = None
        self._running = False
        self._socket_path: str | None = None

    async def start(self) -> None:
        if self._running:
            return

        self._socket_path = getSecureSocketPath()

        if os.name != "nt":
            socket_dir = getSocketDir()

            try:
                dir_stat = Path(socket_dir)
                if dir_stat.exists() and not dir_stat.is_dir():
                    dir_stat.unlink()
            except Exception:
                pass

            Path(socket_dir).mkdir(mode=0o700, parents=True, exist_ok=True)
            try:
                os.chmod(socket_dir, 0o700)
            except Exception:
                pass

            try:
                for entry in Path(socket_dir).iterdir():
                    if entry.name.endswith(".sock"):
                        try:
                            pid = int(entry.name.replace(".sock", ""))
                            try:
                                os.kill(pid, 0)
                            except OSError:
                                entry.unlink()
                        except (ValueError, OSError):
                            pass
            except Exception:
                pass

        _log(f"Creating socket listener: {self._socket_path}")

        if os.name == "nt":
            _log("Windows named pipe server not implemented in Python port")
            self._running = True
            return

        try:
            if Path(self._socket_path).exists():
                Path(self._socket_path).unlink()

            self._server = await asyncio.start_unix_server(
                self._handle_mcp_client, self._socket_path
            )
            os.chmod(self._socket_path, 0o600)
            _log("Socket server listening for connections")
            self._running = True
        except Exception as err:
            _log(f"Socket server error: {err}")
            raise

    async def stop(self) -> None:
        if not self._running:
            return

        for client in list(self._mcp_clients.values()):
            writer: asyncio.StreamWriter | None = client.get("writer")
            if writer:
                try:
                    writer.close()
                except Exception:
                    pass
        self._mcp_clients.clear()

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        if os.name != "nt" and self._socket_path:
            try:
                Path(self._socket_path).unlink()
                _log("Cleaned up socket file")
            except Exception:
                pass

            try:
                socket_dir = getSocketDir()
                remaining = list(Path(socket_dir).iterdir())
                if not remaining:
                    Path(socket_dir).rmdir()
                    _log("Removed empty socket directory")
            except Exception:
                pass

        self._running = False

    async def isRunning(self) -> bool:
        return self._running

    async def getClientCount(self) -> int:
        return len(self._mcp_clients)

    async def handleMessage(self, messageJson: str) -> None:
        try:
            raw_message = json.loads(messageJson)
        except json.JSONDecodeError as e:
            _log(f"Invalid JSON from Chrome: {e}")
            sendChromeMessage(json.dumps({"type": "error", "error": "Invalid message format"}))
            return

        if not isinstance(raw_message, dict) or "type" not in raw_message:
            _log("Invalid message from Chrome: missing type")
            sendChromeMessage(json.dumps({"type": "error", "error": "Invalid message format"}))
            return

        message: dict[str, Any] = raw_message
        _log(f"Handling Chrome message type: {message['type']}")

        msg_type = message["type"]

        if msg_type == "ping":
            _log("Responding to ping")
            sendChromeMessage(json.dumps({"type": "pong", "timestamp": int(datetime.now().timestamp() * 1000)}))

        elif msg_type == "get_status":
            sendChromeMessage(json.dumps({"type": "status_response", "native_host_version": VERSION}))

        elif msg_type == "tool_response":
            if self._mcp_clients:
                _log(f"Forwarding tool response to {len(self._mcp_clients)} MCP clients")
                data = {k: v for k, v in message.items() if k != "type"}
                response_data = json.dumps(data).encode("utf-8")
                length_buffer = struct.pack("<I", len(response_data))
                response_msg = length_buffer + response_data

                for client in list(self._mcp_clients.values()):
                    writer: asyncio.StreamWriter | None = client.get("writer")
                    if writer:
                        try:
                            writer.write(response_msg)
                        except Exception:
                            pass

        elif msg_type == "notification":
            if self._mcp_clients:
                data = {k: v for k, v in message.items() if k != "type"}
                notification_data = json.dumps(data).encode("utf-8")
                length_buffer = struct.pack("<I", len(notification_data))
                notification_msg = length_buffer + notification_data

                for client in list(self._mcp_clients.values()):
                    writer: asyncio.StreamWriter | None = client.get("writer")
                    if writer:
                        try:
                            writer.write(notification_msg)
                        except Exception:
                            pass

        else:
            _log(f"Unknown message type: {msg_type}")
            sendChromeMessage(json.dumps({"type": "error", "error": f"Unknown message type: {msg_type}"}))

    async def _handle_mcp_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        client_id = self._next_client_id
        self._next_client_id += 1

        client: dict[str, Any] = {
            "id": client_id,
            "reader": reader,
            "writer": writer,
            "buffer": b"",
        }
        self._mcp_clients[client_id] = client
        _log(f"MCP client {client_id} connected. Total clients: {len(self._mcp_clients)}")

        sendChromeMessage(json.dumps({"type": "mcp_connected"}))

        try:
            while True:
                data = await reader.read(65536)
                if not data:
                    break

                client["buffer"] += data

                while len(client["buffer"]) >= 4:
                    length = struct.unpack("<I", client["buffer"][:4])[0]

                    if length == 0 or length > MAX_MESSAGE_SIZE:
                        _log(f"Invalid message length from MCP client {client_id}: {length}")
                        writer.close()
                        return

                    if len(client["buffer"]) < 4 + length:
                        break

                    message_bytes = client["buffer"][4:4 + length]
                    client["buffer"] = client["buffer"][4 + length:]

                    try:
                        request = json.loads(message_bytes.decode("utf-8"))
                        _log(f"Forwarding tool request from MCP client {client_id}: {request.get('method')}")

                        sendChromeMessage(json.dumps({
                            "type": "tool_request",
                            "method": request.get("method"),
                            "params": request.get("params"),
                        }))
                    except Exception as e:
                        _log(f"Failed to parse tool request from MCP client {client_id}: {e}")
        except Exception as err:
            _log(f"MCP client {client_id} error: {err}")
        finally:
            _log(f"MCP client {client_id} disconnected. Remaining clients: {len(self._mcp_clients) - 1}")
            self._mcp_clients.pop(client_id, None)
            sendChromeMessage(json.dumps({"type": "mcp_disconnected"}))
            try:
                writer.close()
            except Exception:
                pass


class ChromeMessageReader:
    def __init__(self) -> None:
        self._buffer = b""
        self._pending_resolve: asyncio.Future[str | None] | None = None
        self._closed = False
        self._loop = asyncio.get_event_loop()
        self._setup_stdin()

    def _setup_stdin(self) -> None:
        if sys.platform == "win32":
            import msvcrt
            return

        try:
            self._loop.add_reader(sys.stdin.fileno(), self._on_stdin_data)
        except Exception:
            pass

    def _on_stdin_data(self) -> None:
        try:
            chunk = os.read(sys.stdin.fileno(), 65536)
            if not chunk:
                self._closed = True
                if self._pending_resolve and not self._pending_resolve.done():
                    self._pending_resolve.set_result(None)
                return
            self._buffer += chunk
            self._try_process_message()
        except Exception:
            self._closed = True
            if self._pending_resolve and not self._pending_resolve.done():
                self._pending_resolve.set_result(None)

    def _try_process_message(self) -> None:
        if self._pending_resolve is None or self._pending_resolve.done():
            return

        if len(self._buffer) < 4:
            return

        length = struct.unpack("<I", self._buffer[:4])[0]

        if length == 0 or length > MAX_MESSAGE_SIZE:
            _log(f"Invalid message length: {length}")
            self._pending_resolve.set_result(None)
            return

        if len(self._buffer) < 4 + length:
            return

        message_bytes = self._buffer[4:4 + length]
        self._buffer = self._buffer[4 + length:]

        message = message_bytes.decode("utf-8")
        self._pending_resolve.set_result(message)

    async def read(self) -> str | None:
        if self._closed:
            return None

        if len(self._buffer) >= 4:
            length = struct.unpack("<I", self._buffer[:4])[0]
            if 0 < length <= MAX_MESSAGE_SIZE and len(self._buffer) >= 4 + length:
                message_bytes = self._buffer[4:4 + length]
                self._buffer = self._buffer[4 + length:]
                return message_bytes.decode("utf-8")

        self._pending_resolve = self._loop.create_future()
        self._try_process_message()
        return await self._pending_resolve


async def runChromeNativeHost() -> None:
    _log("Initializing...")

    host = ChromeNativeHost()
    message_reader = ChromeMessageReader()

    await host.start()

    while True:
        message = await message_reader.read()
        if message is None:
            break
        await host.handleMessage(message)

    await host.stop()


send_chrome_message = sendChromeMessage
run_chrome_native_host = runChromeNativeHost


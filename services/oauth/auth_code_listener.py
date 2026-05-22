"""OAuth auth code listener — mirrors src/services/oauth/auth-code-listener.ts."""
from __future__ import annotations

import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Optional
from urllib.parse import parse_qs, urlparse


class AuthCodeListener:
    """Temporary localhost HTTP server that listens for OAuth authorization code redirects.

    Mirrors AuthCodeListener from auth-code-listener.ts.
    """

    def __init__(self, callback_path: str = "/callback") -> None:
        self._callback_path = callback_path
        self._port: int = 0
        self._server: Optional[HTTPServer] = None
        self._auth_code_future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._expected_state: Optional[str] = None

    async def start(self, expected_state: Optional[str] = None) -> int:
        """Start the listener and return the port."""
        self._expected_state = expected_state
        loop = asyncio.get_event_loop()
        future = self._auth_code_future

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass  # silence

            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path != "/callback":
                    self.send_response(404)
                    self.end_headers()
                    return
                params = parse_qs(parsed.query)
                code = params.get("code", [None])[0]
                if code and not future.done():
                    loop.call_soon_threadsafe(future.set_result, code)
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body>Auth complete. You may close this window.</body></html>")

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self._port = self._server.server_address[1]

        def serve():
            self._server.serve_forever()

        Thread(target=serve, daemon=True).start()
        return self._port

    async def wait_for_code(self) -> str:
        """Wait for the authorization code to arrive."""
        return await self._auth_code_future

    async def stop(self) -> None:
        """Stop the listener."""
        if self._server:
            self._server.shutdown()
            self._server = None

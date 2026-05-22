"""Stdlib HTTP server for the Vivian web GUI.

Serves the static frontend, exposes REST endpoints for file/git/search/build
operations, and streams AI responses + subprocess output via SSE. Web Serial
talks to the ESP32 directly from the browser, so the server never touches the
serial port.
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .bridge import EngineBridge, SENTINEL_DONE, sse_frame
from .serial_bridge import bridge as serial_bridge
from . import api as api_mod
from ..gui.chat_config import apply_gui_chat_config, load_gui_chat_config, save_gui_chat_config


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class _Handler(BaseHTTPRequestHandler):
    # Shared state (assigned in launch_web_gui)
    bridge: EngineBridge = None  # type: ignore[assignment]
    runtime: Any = None
    workspace: str = os.getcwd()
    gui_config: dict[str, Any] = {}

    # ── helpers ────────────────────────────────────────────────────────
    def log_message(self, fmt, *args) -> None:  # quiet down access logs
        if os.environ.get("VIVIAN_WEB_DEBUG"):
            super().log_message(fmt, *args)

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text: str, status: int = 200,
                   content_type: str = "text/plain; charset=utf-8") -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, rel: str) -> None:
        path = os.path.normpath(os.path.join(STATIC_DIR, rel.lstrip("/")))
        if not path.startswith(STATIC_DIR) or not os.path.isfile(path):
            self._send_text("not found", 404)
            return
        types = {
            ".html": "text/html; charset=utf-8",
            ".js":   "application/javascript; charset=utf-8",
            ".css":  "text/css; charset=utf-8",
            ".svg":  "image/svg+xml",
            ".ico":  "image/x-icon",
            ".png":  "image/png",
        }
        ctype = types.get(os.path.splitext(path)[1].lower(), "application/octet-stream")
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}

    def _qs(self) -> dict[str, str]:
        parsed = urllib.parse.urlparse(self.path)
        return {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}

    def _run_bridge_coro(self, coro):
        loop = self.bridge.loop if self.bridge else None
        if loop is None:
            raise RuntimeError("engine loop not ready")
        fut = asyncio.run_coroutine_threadsafe(coro, loop)
        return fut.result()

    # ── routing ────────────────────────────────────────────────────────
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        try:
            if path == "/" or path == "/index.html":
                return self._send_static("index.html")
            if path.startswith("/static/"):
                return self._send_static(path[len("/static/"):])

            if path == "/api/health":
                runtime_caps = None
                if self.runtime is not None and hasattr(self.runtime, "get_runtime_capabilities"):
                    try:
                        runtime_caps = self.runtime.get_runtime_capabilities()
                    except Exception:
                        runtime_caps = None
                return self._send_json({"ok": True, "workspace": self.workspace, "runtime": runtime_caps})
            if path == "/api/runtime/capabilities":
                if self.runtime is None or not hasattr(self.runtime, "get_runtime_capabilities"):
                    return self._send_json({"error": "runtime unavailable"}, 503)
                return self._send_json(self.runtime.get_runtime_capabilities())
            if path == "/api/tree":
                return self._send_json(api_mod.list_tree(self._qs().get("path") or self.workspace))
            if path == "/api/file":
                p = self._qs().get("path", "")
                return self._send_json(api_mod.read_file(p))
            if path == "/api/search":
                q = self._qs()
                return self._send_json(api_mod.search(
                    self.workspace,
                    query=q.get("q", ""),
                    case=q.get("case") == "1",
                    word=q.get("word") == "1",
                    regex=q.get("regex") == "1",
                    include=q.get("include", ""),
                    exclude=q.get("exclude", ""),
                ))
            if path == "/api/git/status":
                return self._send_json(api_mod.git_status(self.workspace))
            if path == "/api/build/info":
                return self._send_json(api_mod.build_info(self.workspace, self._qs().get("file", "")))
            if path == "/api/ai/stream":
                return self._stream_ai(self._qs().get("q", ""))
            if path == "/api/ai/stats":
                eng = self.bridge.engine
                ct = eng.cost_tracker
                max_ctx = getattr(eng, "max_tokens", None) or 128000
                cur_tok = getattr(eng, "_current_token_count", 0)
                ctx_pct = round(cur_tok / max_ctx * 100, 1) if max_ctx else 0
                return self._send_json({
                    "input_tokens":  ct.total_input_tokens,
                    "output_tokens": ct.total_output_tokens,
                    "cost_usd":      round(ct.total_cost_usd, 6),
                    "context_pct":   ctx_pct,
                    "context_tokens": cur_tok,
                    "context_max":    max_ctx,
                })
            if path == "/api/gui/config":
                return self._send_json(self.gui_config)
            if path == "/api/run/stream":
                return self._stream_process(self._qs())
            if path == "/api/serial/ports":
                return self._send_json({"ports": serial_bridge.list_ports(),
                                        **serial_bridge.status()})
            if path == "/api/serial/status":
                return self._send_json(serial_bridge.status())
            if path == "/api/serial/stream":
                return self._stream_serial()

            self._send_text("not found", 404)
        except Exception as e:
            self._send_json({"error": f"{type(e).__name__}: {e}"}, 500)

    def do_POST(self) -> None:
        try:
            if self.path == "/api/file":
                body = self._read_body()
                return self._send_json(api_mod.write_file(body.get("path", ""),
                                                          body.get("content", "")))
            if self.path == "/api/workspace":
                body = self._read_body()
                path = body.get("path", "").strip()
                if path and os.path.isdir(path):
                    self.__class__.workspace = os.path.abspath(path)
                    try:
                        os.chdir(self.__class__.workspace)
                        if hasattr(self.bridge.engine, "cwd"):
                            self.bridge.engine.cwd = self.__class__.workspace
                    except OSError:
                        pass
                    return self._send_json({"ok": True, "workspace": self.workspace})
                return self._send_json({"ok": False, "error": "no such directory"}, 400)
            if self.path == "/api/git/action":
                body = self._read_body()
                return self._send_json(api_mod.git_action(self.workspace, body))
            if self.path == "/api/ai/interrupt":
                self.bridge.interrupt()
                return self._send_json({"ok": True})
            if self.path == "/api/gui/config":
                body = self._read_body()
                config = save_gui_chat_config(body.get("config") or {})
                self.__class__.gui_config = apply_gui_chat_config(self.bridge.engine, config)
                return self._send_json(self.gui_config)
            if self.path == "/api/ai/stream":
                body = self._read_body()
                prompt = (body.get("prompt") or "").strip()
                file_context = (body.get("file_context") or "").strip()
                mode_id = (body.get("mode") or "").strip() or None
                if not prompt:
                    return self._send_text("missing prompt", 400)
                return self._stream_ai(prompt, file_context, mode_id=mode_id)
            if self.path == "/api/runtime/command":
                body = self._read_body()
                cmd_line = (body.get("command") or body.get("cmd") or "").strip()
                if not cmd_line:
                    return self._send_json({"error": "missing command"}, 400)
                if self.runtime is None or not hasattr(self.runtime, "execute_slash_command"):
                    return self._send_json({"error": "runtime unavailable"}, 503)
                output = self._run_bridge_coro(self.runtime.execute_slash_command(cmd_line))
                return self._send_json({"ok": True, "command": cmd_line, "output": output})
            if self.path == "/api/runtime/tool":
                body = self._read_body()
                tool_name = (body.get("name") or "").strip()
                tool_args = body.get("args") if isinstance(body.get("args"), dict) else {}
                if not tool_name:
                    return self._send_json({"error": "missing tool name"}, 400)
                if self.runtime is None or not hasattr(self.runtime, "tool_registry"):
                    return self._send_json({"error": "runtime unavailable"}, 503)
                result = self._run_bridge_coro(
                    self.runtime.tool_registry.execute_tool(tool_name, tool_args, {"cwd": self.workspace})
                )
                return self._send_json({"ok": True, "name": tool_name, "result": result})
            if self.path == "/api/serial/open":
                body = self._read_body()
                return self._send_json(serial_bridge.open(
                    body.get("port", ""), int(body.get("baud", 115200))
                ))
            if self.path == "/api/serial/close":
                return self._send_json(serial_bridge.close())
            if self.path == "/api/serial/write":
                body = self._read_body()
                data = body.get("data", "")
                # Accept either plain text or base64
                if body.get("base64"):
                    import base64
                    try:
                        raw = base64.b64decode(data)
                    except Exception as e:
                        return self._send_json({"ok": False, "error": str(e)}, 400)
                else:
                    raw = data.encode("utf-8", errors="replace")
                return self._send_json(serial_bridge.write(raw))

            self._send_text("not found", 404)
        except Exception as e:
            self._send_json({"error": f"{type(e).__name__}: {e}"}, 500)

    # ── streaming endpoints ───────────────────────────────────────────
    def _start_sse(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

    def _stream_ai(self, prompt: str, file_context: str = "", mode_id: str | None = None) -> None:
        prompt = (prompt or "").strip()
        if not prompt:
            self._send_text("missing q", 400)
            return
        if file_context:
            prompt = prompt + file_context
        self._start_sse()
        user_settings = self.gui_config.get("user_settings") or {}
        q = self.bridge.submit(
            prompt,
            mode_id=mode_id or (self._qs().get("mode") or self.gui_config.get("default_mode")),
            is_employee=bool(self.gui_config.get("is_employee")),
            expose_internal_modes=bool(user_settings.get("show_internal_modes")),
        )
        while True:
            event = q.get()
            if event is SENTINEL_DONE:
                try:
                    self.wfile.write(sse_frame({"type": "done"}))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return
            try:
                self.wfile.write(sse_frame(event))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return

    def _stream_serial(self) -> None:
        """SSE stream of bytes from the currently open serial port (base64)."""
        if not serial_bridge.status()["open"]:
            return self._send_json({"error": "no serial port is open — POST /api/serial/open first"}, 409)
        self._start_sse()
        q = serial_bridge.subscribe()
        try:
            self.wfile.write(sse_frame({"type": "open",
                                        "port": serial_bridge.path,
                                        "baud": serial_bridge.baud}))
            self.wfile.flush()
            while True:
                payload = q.get()
                if payload is None:
                    try:
                        self.wfile.write(sse_frame({"type": "closed"}))
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                    return
                try:
                    self.wfile.write(sse_frame({"type": "data", "b64": payload}))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    return
        finally:
            serial_bridge.unsubscribe(q)

    def _stream_process(self, qs: dict) -> None:
        """Run a subprocess and stream its merged stdout+stderr as SSE."""
        kind = qs.get("kind", "")  # 'build' | 'flash' | 'monitor' | 'run' | 'git'
        target = qs.get("target", "")
        method = qs.get("method", "uart")
        argv_raw = qs.get("argv", "")
        file = qs.get("file", "")
        cwd = self.workspace

        argv = api_mod.resolve_run_argv(kind=kind, target=target, method=method,
                                       file=file, argv_raw=argv_raw, cwd=cwd)
        if isinstance(argv, dict) and argv.get("error"):
            self._send_json(argv, 400)
            return

        self._start_sse()
        try:
            self.wfile.write(sse_frame({"type": "started", "argv": argv, "cwd": cwd}))
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return

        import subprocess
        try:
            proc = subprocess.Popen(
                argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                bufsize=1, text=True,
            )
        except FileNotFoundError:
            try:
                self.wfile.write(sse_frame({"type": "error", "error": f"'{argv[0]}' not found on PATH"}))
                self.wfile.write(sse_frame({"type": "done", "code": 127}))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                try:
                    self.wfile.write(sse_frame({"type": "stdout", "text": line}))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    proc.terminate()
                    return
            code = proc.wait()
            try:
                self.wfile.write(sse_frame({"type": "done", "code": code}))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return
        finally:
            if proc.poll() is None:
                proc.terminate()


def launch_web_gui(runtime_or_engine, host: str = "127.0.0.1", port: int = 7878,
                   open_browser: bool = True) -> int:
    """Start the web GUI server. Blocks until Ctrl+C."""
    from ..utils.debug_log import enable_debug, dlog
    enable_debug()
    dlog("web_gui: launch_web_gui host=%s port=%d", host, port)

    runtime = runtime_or_engine if hasattr(runtime_or_engine, "engine") else None
    engine = runtime.engine if runtime is not None else runtime_or_engine

    _Handler.gui_config = apply_gui_chat_config(engine, load_gui_chat_config())
    _Handler.runtime = runtime

    _Handler.bridge = EngineBridge(engine)
    _Handler.workspace = os.path.abspath(getattr(engine, "cwd", None) or os.getcwd())

    httpd = ThreadingHTTPServer((host, port), _Handler)
    url = f"http://{host}:{port}/"
    print(f"\nVivian Web GUI: {url}", file=sys.stderr)
    print("  Open the URL in Chrome or Edge for Web Serial (ESP32 monitor) support.\n", file=sys.stderr)

    if open_browser:
        # Open after the server is bound so the page loads immediately.
        threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down web GUI…", file=sys.stderr)
    finally:
        httpd.shutdown()
        httpd.server_close()
    return 0

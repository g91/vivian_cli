"""Stdlib HTTP server for the Vivian Desktop web GUI.

Serves the cyberpunk desktop frontend and exposes REST endpoints so the
desktop can call back into the full Vivian runtime — commands, tools, skills,
and capabilities.  Mirrors the pattern used by web_gui/server.py.
"""
from __future__ import annotations

import asyncio
import json
import os
import queue
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
APPS_DIR   = os.path.join(os.path.dirname(__file__), "apps")


def _sse_frame(payload: dict) -> bytes:
    return ("data: " + json.dumps(payload, ensure_ascii=False) + "\n\n").encode("utf-8")


_SENTINEL = object()      # marks end of SSE stream


class _Handler(BaseHTTPRequestHandler):
    # Assigned by launch_desktop_gui before the server starts
    runtime: Any = None       # VivianCLI instance (has .engine, .get_runtime_capabilities, etc.)
    workspace: str = os.getcwd()
    ide_url: str = ""         # URL of the companion web_gui IDE (if started together)
    _bridge: Any  = None      # EngineBridge — created lazily on first chat request

    # ── Logging ────────────────────────────────────────────────────────────────
    def log_message(self, fmt, *args) -> None:
        if os.environ.get("VIVIAN_DESKTOP_DEBUG"):
            super().log_message(fmt, *args)

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, rel: str) -> None:
        path = os.path.normpath(os.path.join(STATIC_DIR, rel.lstrip("/")))
        if not path.startswith(STATIC_DIR) or not os.path.isfile(path):
            self._send_json({"error": "not found"}, 404)
            return
        self._serve_file(path)

    def _send_app(self, rel: str) -> None:
        """Serve a file from the apps/ directory."""
        path = os.path.normpath(os.path.join(APPS_DIR, rel.lstrip("/")))
        if not path.startswith(APPS_DIR) or not os.path.isfile(path):
            self._send_json({"error": "app not found"}, 404)
            return
        self._serve_file(path)

    def _serve_file(self, path: str) -> None:
        mime = {
            ".html": "text/html; charset=utf-8",
            ".css":  "text/css; charset=utf-8",
            ".js":   "application/javascript; charset=utf-8",
            ".png":  "image/png",
            ".ico":  "image/x-icon",
            ".svg":  "image/svg+xml",
        }.get(os.path.splitext(path)[1].lower(), "application/octet-stream")
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

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

    def _run_coro(self, coro):
        """Run an async coroutine from a sync handler thread."""
        rt = self.runtime
        loop = getattr(getattr(rt, "_engine", None), "_loop", None) if rt else None
        if loop and loop.is_running():
            fut = asyncio.run_coroutine_threadsafe(coro, loop)
            return fut.result(timeout=30)
        # Fallback: run a fresh event loop on this thread
        return asyncio.run(coro)

    # ── GET ────────────────────────────────────────────────────────────────────
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs   = dict(urllib.parse.parse_qsl(parsed.query))
        try:
            # Desktop shell
            if path in ("/", "/index.html"):
                return self._send_static("index.html")
            # Apps directory
            if path.startswith("/apps/"):
                return self._send_app(path[len("/apps/"):])
            # Other static files (css, js, images)
            if not path.startswith("/api/"):
                return self._send_static(path)

            # ── API ────────────────────────────────────────────────────
            if path == "/api/health":
                caps = None
                if self.runtime and hasattr(self.runtime, "get_runtime_capabilities"):
                    try:
                        caps = self.runtime.get_runtime_capabilities()
                    except Exception:
                        pass
                return self._send_json({
                    "ok": True,
                    "workspace": self.workspace,
                    "ide_url": self.ide_url,
                    "runtime": caps,
                })

            if path == "/api/capabilities":
                if not self.runtime or not hasattr(self.runtime, "get_runtime_capabilities"):
                    return self._send_json({"error": "runtime unavailable"}, 503)
                return self._send_json(self.runtime.get_runtime_capabilities())

            # ── Skills list ────────────────────────────────────────────
            if path == "/api/skills":
                return self._send_json(_skills_list(self.runtime, self.workspace))

            # ── Chat SSE stream ────────────────────────────────────────
            if path == "/api/chat":
                prompt = (qs.get("q") or "").strip()
                if not prompt:
                    return self._send_json({"error": "missing q"}, 400)
                return self._stream_chat(prompt)

            self._send_json({"error": "not found"}, 404)
        except Exception as exc:
            self._send_json({"error": f"{type(exc).__name__}: {exc}"}, 500)

    # ── Chat SSE ───────────────────────────────────────────────────────────────
    def _get_bridge(self):
        """Return (or lazily create) an EngineBridge for chat streaming."""
        if _Handler._bridge is None:
            rt = self.runtime
            engine = getattr(rt, "engine", None)
            if engine is None:
                return None
            try:
                from ..web_gui.bridge import EngineBridge
                _Handler._bridge = EngineBridge(engine)
            except Exception:
                return None
        return _Handler._bridge

    def _stream_chat(self, prompt: str) -> None:
        bridge = self._get_bridge()
        if bridge is None:
            # Fallback: no engine available — execute as slash command
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            try:
                if self.runtime and hasattr(self.runtime, "execute_slash_command"):
                    result = self._run_coro(self.runtime.execute_slash_command(prompt))
                    self.wfile.write(_sse_frame({"type": "chunk", "text": str(result)}))
                else:
                    self.wfile.write(_sse_frame({"type": "error", "error": "runtime unavailable"}))
                self.wfile.write(_sse_frame({"type": "done"}))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        q = bridge.submit(prompt)
        from ..web_gui.bridge import SENTINEL_DONE
        while True:
            event = q.get()
            if event is SENTINEL_DONE:
                try:
                    self.wfile.write(_sse_frame({"type": "done"}))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return
            try:
                self.wfile.write(_sse_frame(event))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return

    # ── POST ───────────────────────────────────────────────────────────────────
    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        try:
            body = self._read_body()

            if path == "/api/launch":
                action = body.get("action", "")
                return self._send_json(_handle_action(action, self.workspace))

            if path == "/api/command":
                # Execute any Vivian slash command and return its output
                cmd_line = (body.get("command") or body.get("cmd") or "").strip()
                if not cmd_line:
                    return self._send_json({"error": "missing command"}, 400)
                if not self.runtime or not hasattr(self.runtime, "execute_slash_command"):
                    return self._send_json({"error": "runtime unavailable"}, 503)
                output = self._run_coro(self.runtime.execute_slash_command(cmd_line))
                return self._send_json({"ok": True, "command": cmd_line, "output": output})

            if path == "/api/tool":
                tool_name = (body.get("name") or "").strip()
                tool_args = body.get("args") if isinstance(body.get("args"), dict) else {}
                if not tool_name:
                    return self._send_json({"error": "missing tool name"}, 400)
                if not self.runtime or not hasattr(self.runtime, "tool_registry"):
                    return self._send_json({"error": "runtime unavailable"}, 503)
                result = self._run_coro(
                    self.runtime.tool_registry.execute_tool(
                        tool_name, tool_args, {"cwd": self.workspace}
                    )
                )
                return self._send_json({"ok": True, "name": tool_name, "result": result})

            # ── Skills management ──────────────────────────────────────
            if path == "/api/skills/toggle":
                name    = (body.get("name") or "").strip()
                enabled = bool(body.get("enabled", True))
                if not name:
                    return self._send_json({"error": "missing name"}, 400)
                result = _skills_toggle(self.runtime, name, enabled)
                return self._send_json(result)

            if path == "/api/skills/create":
                result = _skills_create(
                    name         = (body.get("name") or "").strip(),
                    description  = (body.get("description") or "").strip(),
                    prompt       = (body.get("prompt") or "").strip(),
                    when_to_use  = (body.get("when_to_use") or "").strip(),
                    argument_hint= (body.get("argument_hint") or "").strip(),
                    allowed_tools= body.get("allowed_tools") or [],
                    model        = (body.get("model") or "").strip(),
                    scope        = (body.get("scope") or "user"),
                    workspace    = self.workspace,
                    runtime      = self.runtime,
                )
                return self._send_json(result)

            if path == "/api/skills/delete":
                name = (body.get("name") or "").strip()
                if not name:
                    return self._send_json({"error": "missing name"}, 400)
                result = _skills_delete(name, self.workspace, self.runtime)
                return self._send_json(result)

            self._send_json({"error": "not found"}, 404)
        except Exception as exc:
            self._send_json({"error": f"{type(exc).__name__}: {exc}"}, 500)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


# ── Skills helpers ────────────────────────────────────────────────────────────
# Runtime-level toggle overrides for bundled skills (name → bool).
# Persists only for the lifetime of the server process.
_bundled_toggle_overrides: dict[str, bool] = {}
# Runtime-level toggle overrides for custom skills (name → bool).
_custom_toggle_overrides: dict[str, bool] = {}
_bundled_skills_initialised = False


def _ensure_bundled_skills() -> None:
    global _bundled_skills_initialised
    if _bundled_skills_initialised:
        return
    try:
        from ..skills.bundled import init_bundled_skills
        init_bundled_skills()
    except Exception:
        pass
    _bundled_skills_initialised = True


def _skill_dirs(workspace: str) -> list[str]:
    import pathlib
    dirs = [str(pathlib.Path.home() / ".vivian" / "skills")]
    if workspace:
        dirs.append(str(pathlib.Path(workspace) / ".vivian" / "skills"))
    return dirs


def _skills_list(runtime, workspace: str) -> dict:
    """Return a serializable list of all known skills using the real skill system."""
    import pathlib
    from ..skills.bundled_skills import get_bundled_skills
    from ..skills.load_skills_dir import load_skills_dir

    _ensure_bundled_skills()

    skills: list[dict] = []
    seen: set[str] = set()

    # ── 1. Bundled skills via get_bundled_skills() ────────────────────────────
    for raw in get_bundled_skills():
        name = str(raw.get("name") or "")
        if not name:
            continue
        if raw.get("is_hidden") or not raw.get("user_invocable", True):
            continue

        # is_enabled is a callable or None (None = always enabled)
        is_en = raw.get("is_enabled")
        if name in _bundled_toggle_overrides:
            is_enabled = _bundled_toggle_overrides[name]
        elif callable(is_en):
            try:
                is_enabled = bool(is_en())
            except Exception:
                is_enabled = True
        else:
            is_enabled = True

        skills.append({
            "name":                    name,
            "description":             raw.get("description") or "",
            "aliases":                 list(raw.get("aliases") or []),
            "allowed_tools":           list(raw.get("allowed_tools") or []),
            "argument_hint":           raw.get("argument_hint"),
            "when_to_use":             raw.get("when_to_use"),
            "model":                   raw.get("model"),
            "source":                  "bundled",
            "loaded_from":             "bundled",
            "is_enabled":              is_enabled,
            "disable_model_invocation": bool(raw.get("disable_model_invocation")),
            "context":                 raw.get("context"),
            "agent":                   raw.get("agent"),
            "editable":                False,
        })
        seen.add(name)

    # ── 2. Custom .md skills — walk dirs recursively with load_skills_dir ─────
    dirs = _skill_dirs(workspace)
    for skill_dir_str in dirs:
        skill_dir = pathlib.Path(skill_dir_str)
        if not skill_dir.is_dir():
            continue
        # Scan top-level dir plus every subdirectory (nested support)
        subdirs = sorted(
            [skill_dir] + [d for d in skill_dir.rglob("*") if d.is_dir()]
        )
        for subdir in subdirs:
            for skill in load_skills_dir(subdir):
                if skill.name in seen:
                    continue

                is_en = skill.is_enabled
                if skill.name in _custom_toggle_overrides:
                    is_enabled = _custom_toggle_overrides[skill.name]
                elif callable(is_en):
                    try:
                        is_enabled = bool(is_en())
                    except Exception:
                        is_enabled = True
                else:
                    is_enabled = True

                # Find the actual .md file for editing
                md_candidates = list(subdir.glob(f"{skill.name}.md"))
                md_path = str(md_candidates[0]) if md_candidates else None

                skills.append({
                    "name":                    skill.name,
                    "description":             skill.description or "",
                    "aliases":                 list(skill.aliases or []),
                    "allowed_tools":           list(skill.allowed_tools or []),
                    "argument_hint":           skill.argument_hint,
                    "when_to_use":             skill.when_to_use,
                    "model":                   skill.model,
                    "source":                  "custom",
                    "loaded_from":             str(subdir),
                    "is_enabled":              is_enabled,
                    "disable_model_invocation": bool(skill.disable_model_invocation),
                    "context":                 skill.context,
                    "agent":                   skill.agent,
                    "editable":                True,
                    "file_path":               md_path,
                    "prompt":                  _read_skill_prompt(md_path),
                })
                seen.add(skill.name)

    skills.sort(key=lambda s: (0 if s["source"] == "bundled" else 1, s["name"].lower()))
    return {"skills": skills, "dirs": dirs}


def _read_skill_prompt(md_path) -> str:
    """Return the body (prompt) from a custom .md skill file."""
    if not md_path:
        return ""
    try:
        import re
        text = open(md_path, encoding="utf-8", errors="replace").read()
        if text.startswith("---"):
            end = text.find("---", 3)
            if end != -1:
                return text[end + 3:].lstrip("\n").strip()
        return text.strip()
    except OSError:
        return ""


def _skills_toggle(runtime, name: str, enabled: bool) -> dict:
    """Enable or disable a skill in-process using the real skill system."""
    from ..skills.bundled_skills import get_bundled_skills

    _ensure_bundled_skills()

    # Try bundled first — is_enabled is a callable on the shared dict
    for skill_dict in get_bundled_skills():
        if skill_dict.get("name") == name:
            # Store override; _skills_list reads _bundled_toggle_overrides
            _bundled_toggle_overrides[name] = enabled
            return {"ok": True, "name": name, "is_enabled": enabled, "source": "bundled"}

    # Custom skill — store override in-memory
    _custom_toggle_overrides[name] = enabled
    return {"ok": True, "name": name, "is_enabled": enabled, "source": "custom"}


def _skills_create(
    name: str, description: str, prompt: str,
    triggers: list, when_to_use: str, argument_hint: str,
    allowed_tools: list, model: str, scope: str,
    workspace: str, runtime,
) -> dict:
    """Write a new .md skill file using the format load_skills_dir expects."""
    import pathlib, re as _re

    if not name:
        return {"error": "name is required"}
    if not _re.match(r"^[\w\-]+$", name):
        return {"error": "name must be alphanumeric/dash/underscore only"}
    if not prompt:
        return {"error": "prompt is required"}

    if scope == "project" and workspace:
        skill_dir = pathlib.Path(workspace) / ".vivian" / "skills"
    else:
        skill_dir = pathlib.Path.home() / ".vivian" / "skills"

    skill_dir.mkdir(parents=True, exist_ok=True)
    file_path = skill_dir / f"{name}.md"

    # Build frontmatter exactly as load_skills_dir._parse_frontmatter parses it
    lines: list[str] = ["---"]
    lines.append(f"name: {name}")
    if description:
        lines.append(f"description: {description}")
    if when_to_use:
        lines.append(f"when-to-use: {when_to_use}")
    if argument_hint:
        lines.append(f"argument-hint: {argument_hint}")
    if allowed_tools:
        lines.append(f"allowed-tools: {', '.join(str(t).strip() for t in allowed_tools)}")
    if model:
        lines.append(f"model: {model}")
    lines += ["---", "", prompt.strip(), ""]

    file_path.write_text("\n".join(lines), encoding="utf-8")

    # Live-register using register_bundled_skill so it's immediately usable
    try:
        from ..skills.bundled_skills import BundledSkillDefinition, register_bundled_skill
        _body = prompt.strip()
        register_bundled_skill(BundledSkillDefinition(
            name=name,
            description=description or f"Custom skill: {name}",
            get_prompt_for_command=lambda args="", ctx=None, _b=_body: [{"type": "text", "text": _b}],
            when_to_use=when_to_use or None,
            argument_hint=argument_hint or None,
            allowed_tools=[t.strip() for t in allowed_tools] if allowed_tools else None,
            model=model or None,
            user_invocable=True,
        ))
    except Exception:
        pass

    return {"ok": True, "name": name, "file_path": str(file_path)}


def _skills_delete(name: str, workspace: str, runtime) -> dict:
    """Remove a custom skill .md file from all skill dirs (recursive)."""
    import pathlib

    deleted: list[str] = []
    for d in _skill_dirs(workspace):
        p = pathlib.Path(d)
        if not p.is_dir():
            continue
        for md in p.rglob(f"{name}.md"):
            md.unlink()
            deleted.append(str(md))

    # Clear any toggle override
    _custom_toggle_overrides.pop(name, None)

    if deleted:
        return {"ok": True, "deleted": deleted}
    return {"ok": False, "error": f"no file found for skill '{name}'"}


# ── Desktop action dispatcher ─────────────────────────────────────────────────
def _handle_action(action: str, workspace: str) -> dict:
    """Open system apps and browser URLs triggered by desktop icon double-clicks."""
    import subprocess
    import sys

    _sys_cmds: dict[str, list[str]] = {
        "terminal": ["cmd.exe"] if sys.platform == "win32" else ["bash"],
        "files":    (["explorer.exe", workspace] if sys.platform == "win32"
                     else ["xdg-open", workspace]),
        "editor":   ["code", workspace],
    }
    if action in _sys_cmds:
        try:
            subprocess.Popen(_sys_cmds[action])
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
    # Web/browser actions are handled client-side (window.open) — just ack them
    return {"ok": True, "client_handled": True}


# ── Entry point ───────────────────────────────────────────────────────────────
def launch_desktop_gui(
    runtime: Any = None,
    host: str = "127.0.0.1",
    port: int = 7979,
    open_browser: bool = True,
    workspace: str = "",
    ide_url: str = "",
) -> None:
    """Start the Vivian Desktop web GUI server (blocking).

    Args:
        runtime:      VivianCLI instance — gives the desktop access to all tools,
                      commands, skills, and the AI engine.
        host:         Interface to bind (default 127.0.0.1).
        port:         TCP port (default 7979).
        open_browser: Auto-open the desktop in the default browser.
        workspace:    Working directory shown on the desktop.
        ide_url:      URL of the companion web_gui IDE, injected into /api/health
                      so the desktop can link its IDE icon.
    """
    _Handler.runtime  = runtime
    _Handler.workspace = workspace or os.getcwd()
    _Handler.ide_url   = ide_url

    server = ThreadingHTTPServer((host, port), _Handler)
    url = f"http://{host}:{port}/"
    print(f"[Vivian Desktop] Running at {url}")
    if ide_url:
        print(f"[Vivian Desktop] IDE linked at {ide_url}")

    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()

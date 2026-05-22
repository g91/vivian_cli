"""Port of src/bridge/sessionRunner.ts

Session spawner — forks child vivian Code processes for bridge sessions.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .debugUtils import debugTruncate
from .types import SessionActivity, SessionDoneStatus, SessionHandle, SessionSpawnOpts, SessionSpawner

MAX_ACTIVITIES = 10
MAX_STDERR_LINES = 10

TOOL_VERBS: Dict[str, str] = {
    "Read": "Reading",
    "Write": "Writing",
    "Edit": "Editing",
    "MultiEdit": "Editing",
    "Bash": "Running",
    "Glob": "Searching",
    "Grep": "Searching",
    "WebFetch": "Fetching",
    "WebSearch": "Searching",
    "Task": "Running task",
    "FileReadTool": "Reading",
    "FileWriteTool": "Writing",
    "FileEditTool": "Editing",
    "GlobTool": "Searching",
    "GrepTool": "Searching",
    "BashTool": "Running",
    "NotebookEditTool": "Editing notebook",
    "LSP": "LSP",
}


def safeFilenameId(id_: str) -> str:
    """Sanitize a session ID for use in file names."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", id_)


def _tool_summary(name: str, input_: Dict[str, Any]) -> str:
    verb = TOOL_VERBS.get(name, name)
    target = (
        input_.get("file_path")
        or input_.get("filePath")
        or input_.get("pattern")
        or (str(input_.get("command", ""))[:60] if "command" in input_ else None)
        or input_.get("url")
        or input_.get("query")
        or ""
    )
    if target:
        return f"{verb} {target}"
    return verb


def _input_preview(input_: Dict[str, Any]) -> str:
    parts = []
    for key, val in input_.items():
        if isinstance(val, str):
            parts.append(f'{key}="{val[:100]}"')
        if len(parts) >= 3:
            break
    return " ".join(parts)


def extractActivities(line: str, session_id: str, on_debug: Callable[[str], None]) -> List[SessionActivity]:
    try:
        msg = json.loads(line)
    except Exception:
        return []
    if not isinstance(msg, dict):
        return []

    activities: List[SessionActivity] = []
    now = int(asyncio.get_event_loop().time() * 1000) if asyncio.get_event_loop().is_running() else 0

    msg_type = msg.get("type")
    if msg_type == "assistant":
        message = msg.get("message", {})
        content = message.get("content", []) if isinstance(message, dict) else []
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    name = block.get("name", "Tool")
                    inp = block.get("input", {})
                    summary = _tool_summary(name, inp)
                    activities.append(SessionActivity(type="tool_start", summary=summary, timestamp=now))
                    on_debug(f"[bridge:activity] sessionId={session_id} tool_use name={name} {_input_preview(inp)}")
                elif block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        activities.append(SessionActivity(type="text", summary=text[:80], timestamp=now))
                        on_debug(f'[bridge:activity] sessionId={session_id} text "{text[:100]}"')
    elif msg_type == "result":
        subtype = msg.get("subtype")
        if subtype == "success":
            activities.append(SessionActivity(type="result", summary="Session completed", timestamp=now))
            on_debug(f"[bridge:activity] sessionId={session_id} result subtype=success")
        elif subtype:
            errors = msg.get("errors", [])
            error_summary = errors[0] if errors else f"Error: {subtype}"
            activities.append(SessionActivity(type="error", summary=error_summary, timestamp=now))
            on_debug(f'[bridge:activity] sessionId={session_id} result subtype={subtype} error="{error_summary}"')

    return activities


def _extract_user_message_text(msg: Dict[str, Any]) -> Optional[str]:
    """Extract plain text from a replayed user message."""
    if msg.get("parent_tool_use_id") is not None or msg.get("isSynthetic") or msg.get("isReplay"):
        return None
    message = msg.get("message", {})
    content = message.get("content") if isinstance(message, dict) else None
    text: Optional[str] = None
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                break
    text = text.strip() if text else None
    return text or None


class _SessionHandleImpl(SessionHandle):
    def __init__(
        self,
        session_id: str,
        proc: subprocess.Popen,
        done_future: "asyncio.Future[str]",
        activities: List[SessionActivity],
        last_stderr: List[str],
        access_token: str,
        on_debug: Callable[[str], None],
    ) -> None:
        self.sessionId = session_id
        self._proc = proc
        self._done_future = done_future
        self.activities = activities
        self.lastStderr = last_stderr
        self.accessToken = access_token
        self._on_debug = on_debug
        self._current_activity: Optional[SessionActivity] = None
        self._sigkill_sent = False

    @property
    def currentActivity(self) -> Optional[SessionActivity]:
        return self._current_activity

    @property
    def done(self):
        return self._done_future

    def kill(self) -> None:
        if self._proc.poll() is None:
            self._on_debug(f"[bridge:session] Sending SIGTERM to sessionId={self.sessionId} pid={self._proc.pid}")
            try:
                if sys.platform == "win32":
                    self._proc.terminate()
                else:
                    self._proc.send_signal(signal.SIGTERM)
            except Exception:
                pass

    def forceKill(self) -> None:
        if not self._sigkill_sent and self._proc.pid:
            self._sigkill_sent = True
            self._on_debug(f"[bridge:session] Sending SIGKILL to sessionId={self.sessionId} pid={self._proc.pid}")
            try:
                if sys.platform == "win32":
                    self._proc.kill()
                else:
                    self._proc.send_signal(signal.SIGKILL)
            except Exception:
                pass

    def writeStdin(self, data: str) -> None:
        if self._proc.stdin and not self._proc.stdin.closed:
            self._on_debug(f"[bridge:ws] sessionId={self.sessionId} >>> {debugTruncate(data)}")
            try:
                self._proc.stdin.write(data.encode())
                self._proc.stdin.flush()
            except Exception:
                pass

    def updateAccessToken(self, token: str) -> None:
        self.accessToken = token
        msg = json.dumps({
            "type": "update_environment_variables",
            "variables": {"vivian_CODE_SESSION_ACCESS_TOKEN": token},
        }) + "\n"
        self.writeStdin(msg)
        self._on_debug(f"[bridge:session] Sent token refresh via stdin for sessionId={self.sessionId}")


def createSessionSpawner(
    exec_path: str,
    script_args: List[str],
    env: Dict[str, str],
    verbose: bool,
    sandbox: bool,
    debug_file: Optional[str] = None,
    permission_mode: Optional[str] = None,
    on_debug: Optional[Callable[[str], None]] = None,
    on_activity: Optional[Callable[[str, SessionActivity], None]] = None,
    on_permission_request: Optional[Callable] = None,
) -> SessionSpawner:
    def _debug(msg: str) -> None:
        if on_debug:
            on_debug(msg)

    class _Spawner(SessionSpawner):
        def spawn(self, opts: SessionSpawnOpts, directory: str) -> SessionHandle:
            safe_id = safeFilenameId(opts["sessionId"])
            dbf: Optional[str] = None
            if debug_file:
                ext_idx = debug_file.rfind(".")
                if ext_idx > 0:
                    dbf = f"{debug_file[:ext_idx]}-{safe_id}{debug_file[ext_idx:]}"
                else:
                    dbf = f"{debug_file}-{safe_id}"
            elif verbose or os.environ.get("USER_TYPE") == "ant":
                dbf = os.path.join(tempfile.gettempdir(), "vivian", f"bridge-session-{safe_id}.log")

            args = [
                exec_path,
                *script_args,
                "--print",
                "--sdk-url", opts["sdkUrl"],
                "--session-id", opts["sessionId"],
                "--input-format", "stream-json",
                "--output-format", "stream-json",
                "--replay-user-messages",
                *(["--verbose"] if verbose else []),
                *(["--debug-file", dbf] if dbf else []),
                *(["--permission-mode", permission_mode] if permission_mode else []),
            ]

            child_env = {**env}
            child_env.pop("vivian_CODE_OAUTH_TOKEN", None)
            child_env["vivian_CODE_ENVIRONMENT_KIND"] = "bridge"
            child_env["vivian_CODE_SESSION_ACCESS_TOKEN"] = opts["accessToken"]
            child_env["vivian_CODE_POST_FOR_SESSION_INGRESS_V2"] = "1"
            if sandbox:
                child_env["vivian_CODE_FORCE_SANDBOX"] = "1"
            if opts.get("useCcrV2"):
                child_env["vivian_CODE_USE_CCR_V2"] = "1"
                child_env["vivian_CODE_WORKER_EPOCH"] = str(opts.get("workerEpoch", 0))

            _debug(f"[bridge:session] Spawning sessionId={opts['sessionId']} sdkUrl={opts['sdkUrl']} accessToken={'present' if opts['accessToken'] else 'MISSING'}")
            _debug(f"[bridge:session] Child args: {' '.join(args[1:])}")
            if dbf:
                _debug(f"[bridge:session] Debug log: {dbf}")

            proc = subprocess.Popen(
                args,
                cwd=directory,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=child_env,
            )
            _debug(f"[bridge:session] sessionId={opts['sessionId']} pid={proc.pid}")

            activities: List[SessionActivity] = []
            last_stderr: List[str] = []

            loop = asyncio.get_event_loop()
            done_future: asyncio.Future = loop.create_future()

            handle = _SessionHandleImpl(
                session_id=opts["sessionId"],
                proc=proc,
                done_future=done_future,
                activities=activities,
                last_stderr=last_stderr,
                access_token=opts["accessToken"],
                on_debug=_debug,
            )

            async def _watch_stderr():
                if proc.stderr:
                    import io
                    reader = io.TextIOWrapper(proc.stderr, encoding="utf-8", errors="replace")
                    for line in reader:
                        line = line.rstrip("\n")
                        if verbose:
                            sys.stderr.write(line + "\n")
                        if len(last_stderr) >= MAX_STDERR_LINES:
                            last_stderr.pop(0)
                        last_stderr.append(line)

            async def _watch_stdout():
                first_user_seen = False
                if proc.stdout:
                    import io
                    reader = io.TextIOWrapper(proc.stdout, encoding="utf-8", errors="replace")
                    for line in reader:
                        line = line.rstrip("\n")
                        _debug(f"[bridge:ws] sessionId={opts['sessionId']} <<< {debugTruncate(line)}")
                        if verbose:
                            sys.stderr.write(line + "\n")

                        extracted = extractActivities(line, opts["sessionId"], _debug)
                        for act in extracted:
                            if len(activities) >= MAX_ACTIVITIES:
                                activities.pop(0)
                            activities.append(act)
                            handle._current_activity = act
                            if on_activity:
                                on_activity(opts["sessionId"], act)

                        try:
                            msg = json.loads(line)
                            if isinstance(msg, dict):
                                if msg.get("type") == "control_request":
                                    req = msg.get("request", {})
                                    if req.get("subtype") == "can_use_tool" and on_permission_request:
                                        on_permission_request(opts["sessionId"], msg, opts["accessToken"])
                                elif (msg.get("type") == "user" and not first_user_seen and opts.get("onFirstUserMessage")):
                                    text = _extract_user_message_text(msg)
                                    if text:
                                        first_user_seen = True
                                        opts["onFirstUserMessage"](text)
                        except Exception:
                            pass

            async def _wait_proc():
                await asyncio.gather(
                    asyncio.get_event_loop().run_in_executor(None, _watch_stderr_sync),
                    asyncio.get_event_loop().run_in_executor(None, _watch_stdout_sync),
                )
                ret = proc.wait()
                if ret == 0:
                    status = "completed"
                elif ret < 0:
                    status = "interrupted"
                else:
                    status = "failed"
                _debug(f"[bridge:session] sessionId={opts['sessionId']} {status} exit_code={ret} pid={proc.pid}")
                if not done_future.done():
                    done_future.set_result(status)

            def _watch_stderr_sync():
                if proc.stderr:
                    import io
                    reader = io.TextIOWrapper(proc.stderr, errors="replace")
                    for line in reader:
                        line = line.rstrip("\n")
                        if verbose:
                            sys.stderr.write(line + "\n")
                        if len(last_stderr) >= MAX_STDERR_LINES:
                            last_stderr.pop(0)
                        last_stderr.append(line)

            def _watch_stdout_sync():
                first_user_seen = False
                if proc.stdout:
                    import io
                    reader = io.TextIOWrapper(proc.stdout, errors="replace")
                    for line in reader:
                        line = line.rstrip("\n")
                        _debug(f"[bridge:ws] sessionId={opts['sessionId']} <<< {debugTruncate(line)}")
                        if verbose:
                            sys.stderr.write(line + "\n")

                        extracted = extractActivities(line, opts["sessionId"], _debug)
                        for act in extracted:
                            if len(activities) >= MAX_ACTIVITIES:
                                activities.pop(0)
                            activities.append(act)
                            handle._current_activity = act
                            if on_activity:
                                on_activity(opts["sessionId"], act)

                        try:
                            msg = json.loads(line)
                            if isinstance(msg, dict):
                                if msg.get("type") == "control_request":
                                    req = msg.get("request", {})
                                    if req.get("subtype") == "can_use_tool" and on_permission_request:
                                        on_permission_request(opts["sessionId"], msg, opts["accessToken"])
                        except Exception:
                            pass

            asyncio.ensure_future(_wait_proc())
            return handle

    return _Spawner()

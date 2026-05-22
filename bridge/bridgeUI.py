"""Port of src/bridge/bridgeUI.ts

Bridge logger/UI implementation — console status line with QR code,
spinner, per-session display, and reconnect animations.
"""
from __future__ import annotations

import asyncio
import math
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional

from .bridgeStatusUtil import (
    buildActiveFooterText,
    buildBridgeConnectUrl,
    buildBridgeSessionUrl,
    buildIdleFooterText,
    formatDuration,
    timestamp,
    truncatePrompt,
    wrapWithOsc8Link,
    FAILED_FOOTER_TEXT,
    TOOL_DISPLAY_EXPIRY_MS,
)
from .types import BridgeConfig, BridgeLogger, SessionActivity, SpawnMode

try:
    from ..constants.figures import BRIDGE_FAILED_INDICATOR, BRIDGE_READY_INDICATOR, BRIDGE_SPINNER_FRAMES
except Exception:
    BRIDGE_FAILED_INDICATOR = "✗"
    BRIDGE_READY_INDICATOR = "●"
    BRIDGE_SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


def _string_width(s: str) -> int:
    """Approximate string display width (ignores ANSI escape codes)."""
    import re
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    clean = ansi_escape.sub("", s)
    return len(clean)


def _dim(s: str) -> str:
    return f"\033[2m{s}\033[0m"


def _green(s: str) -> str:
    return f"\033[32m{s}\033[0m"


def _cyan(s: str) -> str:
    return f"\033[36m{s}\033[0m"


def _red(s: str) -> str:
    return f"\033[31m{s}\033[0m"


def _yellow(s: str) -> str:
    return f"\033[33m{s}\033[0m"


def _white(s: str) -> str:
    return f"\033[97m{s}\033[0m"


async def _generate_qr(url: str) -> List[str]:
    try:
        import qrcode  # type: ignore
        from io import StringIO
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        f = StringIO()
        qr.print_ascii(out=f)
        f.seek(0)
        lines = [l for l in f.read().split("\n") if l]
        return lines
    except Exception:
        return []


class _ConsoleBridgeLogger(BridgeLogger):
    """Console-based BridgeLogger implementation."""

    def __init__(self, verbose: bool, write: Optional[Callable[[str], None]] = None) -> None:
        self._verbose = verbose
        self._write = write or (lambda s: sys.stdout.write(s) or sys.stdout.flush())
        self._status_line_count = 0
        self._current_state = "idle"
        self._current_state_text = "Ready"
        self._repo_name = ""
        self._branch = ""
        self._debug_log_path = ""
        self._connect_url = ""
        self._cached_ingress_url = ""
        self._cached_environment_id = ""
        self._active_session_url: Optional[str] = None
        self._qr_lines: List[str] = []
        self._qr_visible = False
        self._last_tool_summary: Optional[str] = None
        self._last_tool_time = 0
        self._session_active = 0
        self._session_max = 1
        self._spawn_mode_display: Optional[str] = None
        self._spawn_mode: SpawnMode = "single-session"
        self._session_display_info: Dict[str, Dict[str, Any]] = {}
        self._connecting_tick = 0
        self._connecting_task: Optional[asyncio.Task] = None

    def _count_visual_lines(self, text: str) -> int:
        cols = os.get_terminal_size().columns if hasattr(os, "get_terminal_size") else 80
        try:
            cols = os.get_terminal_size().columns
        except Exception:
            cols = 80
        count = 0
        for logical in text.split("\n"):
            if not logical:
                count += 1
                continue
            width = _string_width(logical)
            count += max(1, math.ceil(width / cols))
        if text.endswith("\n"):
            count -= 1
        return count

    def _write_status(self, text: str) -> None:
        self._write(text)
        self._status_line_count += self._count_visual_lines(text)

    def _clear_status_lines(self) -> None:
        if self._status_line_count <= 0:
            return
        self._write(f"\x1b[{self._status_line_count}A")
        self._write("\x1b[J")
        self._status_line_count = 0

    def _print_log(self, line: str) -> None:
        self._clear_status_lines()
        self._write(line)

    def _regenerate_qr(self, url: str) -> None:
        async def _do():
            lines = await _generate_qr(url)
            self._qr_lines = lines
            self._render_status_line()
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(_do())
        except Exception:
            pass

    def _render_connecting_line(self) -> None:
        self._clear_status_lines()
        frame = BRIDGE_SPINNER_FRAMES[self._connecting_tick % len(BRIDGE_SPINNER_FRAMES)]
        suffix = ""
        if self._repo_name:
            suffix += _dim(f" · {self._repo_name}")
        if self._branch:
            suffix += _dim(f" · {self._branch}")
        self._write_status(f"{_yellow(frame)} {_yellow('Connecting')}{suffix}\n")

    def _stop_connecting(self) -> None:
        if self._connecting_task:
            self._connecting_task.cancel()
            self._connecting_task = None

    def _start_connecting(self) -> None:
        self._stop_connecting()
        self._render_connecting_line()
        async def _spinner_loop():
            try:
                while True:
                    await asyncio.sleep(0.15)
                    self._connecting_tick += 1
                    self._render_connecting_line()
            except asyncio.CancelledError:
                pass
        try:
            self._connecting_task = asyncio.ensure_future(_spinner_loop())
        except RuntimeError:
            pass

    def _render_status_line(self) -> None:
        if self._current_state in ("reconnecting", "failed"):
            return
        self._clear_status_lines()
        is_idle = self._current_state == "idle"
        if self._qr_visible:
            for line in self._qr_lines:
                self._write_status(f"{_dim(line)}\n")

        indicator = BRIDGE_READY_INDICATOR
        if is_idle:
            state_text = _green(self._current_state_text)
            indicator_colored = _green(indicator)
        else:
            state_text = _cyan(self._current_state_text)
            indicator_colored = _cyan(indicator)

        suffix = ""
        if self._repo_name:
            suffix += _dim(f" · {self._repo_name}")
        if self._branch and self._spawn_mode != "worktree":
            suffix += _dim(f" · {self._branch}")

        if os.environ.get("USER_TYPE") == "ant" and self._debug_log_path:
            self._write_status(f"{_yellow('[ANT-ONLY] Logs:')} {_dim(self._debug_log_path)}\n")

        self._write_status(f"{indicator_colored} {state_text}{suffix}\n")

        if self._session_max > 1:
            mode_hint = (
                "New sessions will be created in an isolated worktree"
                if self._spawn_mode == "worktree"
                else "New sessions will be created in the current directory"
            )
            self._write_status(f"    {_dim(f'Capacity: {self._session_active}/{self._session_max} · {mode_hint}')}\n")
            for sid, info in self._session_display_info.items():
                title_text = truncatePrompt(info.get("title", ""), 35) if info.get("title") else _dim("Attached")
                title_linked = wrapWithOsc8Link(title_text, info.get("url", ""))
                act = info.get("activity")
                show_act = act and act.get("type") not in ("result", "error")
                act_text = _dim(f" {truncatePrompt(act['summary'], 40)}") if show_act and act else ""
                self._write_status(f"    {title_linked}{act_text}\n")
        elif self._session_max == 1:
            if self._spawn_mode == "single-session":
                mode_text = "Single session · exits when complete"
            elif self._spawn_mode == "worktree":
                mode_text = f"Capacity: {self._session_active}/1 · New sessions will be created in an isolated worktree"
            else:
                mode_text = f"Capacity: {self._session_active}/1 · New sessions will be created in the current directory"
            self._write_status(f"    {_dim(mode_text)}\n")

        if (self._session_max == 1 and not is_idle and self._last_tool_summary
                and time.time() * 1000 - self._last_tool_time < TOOL_DISPLAY_EXPIRY_MS):
            self._write_status(f"  {_dim(truncatePrompt(self._last_tool_summary, 60))}\n")

        url = self._active_session_url or self._connect_url
        if url:
            self._write_status("\n")
            footer = buildIdleFooterText(url) if is_idle else buildActiveFooterText(url)
            qr_hint = _dim("space to hide QR code") if self._qr_visible else _dim("space to show QR code")
            toggle_hint = _dim(" · w to toggle spawn mode") if self._spawn_mode_display else ""
            self._write_status(f"{_dim(footer)}\n")
            self._write_status(f"{qr_hint}{toggle_hint}\n")

    # ─── BridgeLogger interface ──────────────────────────────────────────────

    def printBanner(self, config: BridgeConfig, environment_id: str) -> None:
        self._cached_ingress_url = config.get("sessionIngressUrl", "")
        self._cached_environment_id = environment_id
        self._connect_url = buildBridgeConnectUrl(environment_id, self._cached_ingress_url)
        self._regenerate_qr(self._connect_url)
        if self._verbose:
            self._write(f"Remote Control\n")
        if self._verbose:
            if config.get("spawnMode") != "single-session":
                self._write(f"Spawn mode: {config.get('spawnMode')}\n")
                self._write(f"Max concurrent sessions: {config.get('maxSessions')}\n")
            self._write(f"Environment ID: {environment_id}\n")
        if config.get("sandbox"):
            self._write(f"Sandbox: {_green('Enabled')}\n")
        self._write("\n")
        self._start_connecting()

    def logSessionStart(self, session_id: str, prompt: str) -> None:
        if self._verbose:
            short = truncatePrompt(prompt, 80)
            self._print_log(f"{_dim(f'[{timestamp()}]')} Session started: {_white(chr(34) + short + chr(34))} ({_dim(session_id)})\n")

    def logSessionComplete(self, session_id: str, duration_ms: int) -> None:
        self._print_log(f"{_dim(f'[{timestamp()}]')} Session {_green('completed')} ({formatDuration(duration_ms)}) {_dim(session_id)}\n")

    def logSessionFailed(self, session_id: str, error: str) -> None:
        self._print_log(f"{_dim(f'[{timestamp()}]')} Session {_red('failed')}: {error} {_dim(session_id)}\n")

    def logStatus(self, message: str) -> None:
        self._print_log(f"{_dim(f'[{timestamp()}]')} {message}\n")

    def logVerbose(self, message: str) -> None:
        if self._verbose:
            self._print_log(f"{_dim(f'[{timestamp()}] {message}')}\n")

    def logError(self, message: str) -> None:
        self._print_log(f"{_red(f'[{timestamp()}] Error: {message}')}\n")

    def logReconnected(self, disconnected_ms: int) -> None:
        self._print_log(f"{_dim(f'[{timestamp()}]')} {_green('Reconnected')} after {formatDuration(disconnected_ms)}\n")

    def setRepoInfo(self, repo_name: str, branch: str) -> None:
        self._repo_name = repo_name
        self._branch = branch

    def setDebugLogPath(self, path: str) -> None:
        self._debug_log_path = path

    def updateIdleStatus(self) -> None:
        self._stop_connecting()
        self._current_state = "idle"
        self._current_state_text = "Ready"
        self._last_tool_summary = None
        self._last_tool_time = 0
        self._active_session_url = None
        self._regenerate_qr(self._connect_url)
        self._render_status_line()

    def setAttached(self, session_id: str) -> None:
        self._stop_connecting()
        self._current_state = "attached"
        self._current_state_text = "Connected"
        self._last_tool_summary = None
        self._last_tool_time = 0
        if self._session_max <= 1:
            self._active_session_url = buildBridgeSessionUrl(
                session_id, self._cached_environment_id, self._cached_ingress_url
            )
            self._regenerate_qr(self._active_session_url)
        self._render_status_line()

    def updateReconnectingStatus(self, delay_str: str, elapsed_str: str) -> None:
        self._stop_connecting()
        self._clear_status_lines()
        self._current_state = "reconnecting"
        if self._qr_visible:
            for line in self._qr_lines:
                self._write_status(f"{_dim(line)}\n")
        frame = BRIDGE_SPINNER_FRAMES[self._connecting_tick % len(BRIDGE_SPINNER_FRAMES)]
        self._connecting_tick += 1
        self._write_status(f"{_yellow(frame)} {_yellow('Reconnecting')} {_dim('·')} {_dim(f'retrying in {delay_str}')} {_dim('·')} {_dim(f'disconnected {elapsed_str}')}\n")

    def updateFailedStatus(self, error: str) -> None:
        self._stop_connecting()
        self._clear_status_lines()
        self._current_state = "failed"
        suffix = ""
        if self._repo_name:
            suffix += _dim(f" · {self._repo_name}")
        if self._branch:
            suffix += _dim(f" · {self._branch}")
        self._write_status(f"{_red(BRIDGE_FAILED_INDICATOR)} {_red('Remote Control Failed')}{suffix}\n")
        self._write_status(f"{_dim(FAILED_FOOTER_TEXT)}\n")
        if error:
            self._write_status(f"{_red(error)}\n")

    def updateSessionStatus(self, session_id: str, elapsed: str, activity: SessionActivity, trail: List[str]) -> None:
        if activity.get("type") == "tool_start":
            self._last_tool_summary = activity.get("summary")
            self._last_tool_time = time.time() * 1000
        self._render_status_line()

    def clearStatus(self) -> None:
        self._stop_connecting()
        self._clear_status_lines()

    def toggleQr(self) -> None:
        self._qr_visible = not self._qr_visible
        self._render_status_line()

    def updateSessionCount(self, active: int, max_sessions: int, mode: SpawnMode) -> None:
        if self._session_active == active and self._session_max == max_sessions and self._spawn_mode == mode:
            return
        self._session_active = active
        self._session_max = max_sessions
        self._spawn_mode = mode

    def setSpawnModeDisplay(self, mode: Optional[str]) -> None:
        if self._spawn_mode_display == mode:
            return
        self._spawn_mode_display = mode
        if mode:
            self._spawn_mode = mode  # type: ignore[assignment]

    def addSession(self, session_id: str, url: str) -> None:
        self._session_display_info[session_id] = {"url": url}

    def updateSessionActivity(self, session_id: str, activity: SessionActivity) -> None:
        info = self._session_display_info.get(session_id)
        if info:
            info["activity"] = activity

    def setSessionTitle(self, session_id: str, title: str) -> None:
        info = self._session_display_info.get(session_id)
        if not info:
            return
        info["title"] = title
        if self._current_state in ("reconnecting", "failed"):
            return
        if self._session_max == 1:
            self._current_state = "titled"
            self._current_state_text = truncatePrompt(title, 40)
        self._render_status_line()

    def removeSession(self, session_id: str) -> None:
        self._session_display_info.pop(session_id, None)

    def refreshDisplay(self) -> None:
        if self._current_state in ("reconnecting", "failed"):
            return
        self._render_status_line()


def createBridgeLogger(verbose: bool, write: Optional[Callable[[str], None]] = None) -> BridgeLogger:
    """Create a console bridge logger."""
    return _ConsoleBridgeLogger(verbose, write)

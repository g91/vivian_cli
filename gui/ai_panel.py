"""Vivian AI chat panel.

The engine is async, Qt is not. We run a private asyncio loop in a worker
thread and bridge results to the UI thread via Qt signals.
"""
from __future__ import annotations
import asyncio
import threading
from typing import Any, Optional

from PyQt6.QtCore import QObject, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QKeyEvent, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QTextEdit,
    QVBoxLayout, QWidget,
)

from .chat_config import get_gui_chat_config_path, load_gui_chat_config
from .chat_modes import compose_mode_prompt


class EngineWorker(QObject):
    """Owns a background asyncio loop and forwards engine events as signals."""
    chunk_ready = pyqtSignal(str)
    tool_result = pyqtSignal(str, dict)
    system_msg = pyqtSignal(str)
    error = pyqtSignal(str)
    command_output = pyqtSignal(str)
    done = pyqtSignal()

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="VivianEngine")
        self._thread.start()
        self._ready.wait(timeout=2.0)
        self._current: Optional[asyncio.Future] = None

    def _run_loop(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._ready.set()
        try:
            self.loop.run_forever()
        finally:
            self.loop.close()

    def submit(self, prompt: str, mode_prompt: Optional[str] = None) -> None:
        if self.loop is None:
            self.error.emit("Engine loop not ready")
            return
        self._current = asyncio.run_coroutine_threadsafe(self._consume(prompt, mode_prompt=mode_prompt), self.loop)

    def submit_command(self, cmd_line: str, command_handler) -> None:
        if self.loop is None:
            self.error.emit("Engine loop not ready")
            return
        self._current = asyncio.run_coroutine_threadsafe(
            self._consume_command(cmd_line, command_handler),
            self.loop,
        )

    def interrupt(self) -> None:
        try:
            self.engine.interrupt()
        except Exception:
            pass

    def shutdown(self) -> None:
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)

    async def _consume(self, prompt: str, mode_prompt: Optional[str] = None) -> None:
        try:
            effective_prompt = mode_prompt or prompt
            async for event in self.engine.submit_message(effective_prompt):
                # Stream chunks: extract delta.content
                if hasattr(event, "choices"):
                    for choice in getattr(event, "choices", []):
                        delta = choice.get("delta", {})
                        content = delta.get("content") or ""
                        if content:
                            self.chunk_ready.emit(content)
                    continue
                if isinstance(event, dict):
                    if event.get("type") == "tool_result":
                        self.tool_result.emit(
                            event.get("tool_name", "?"),
                            event.get("result") or {},
                        )
                        continue
                    if "choices" in event:
                        for choice in event["choices"]:
                            delta = choice.get("delta", {})
                            content = delta.get("content") or ""
                            if content:
                                self.chunk_ready.emit(content)
                        continue
                role = getattr(event, "role", None)
                content = getattr(event, "content", None)
                if role == "system" and content:
                    self.system_msg.emit(str(content))
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}")
        finally:
            self.done.emit()

    async def _consume_command(self, cmd_line: str, command_handler) -> None:
        try:
            result = command_handler(cmd_line)
            if asyncio.iscoroutine(result):
                result = await result
            self.command_output.emit(str(result or "(no output)"))
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}")
        finally:
            self.done.emit()


class _ChatInput(QPlainTextEdit):
    """Multi-line input that submits on Enter, newline on Shift+Enter."""
    submit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Ask Vivian… (Enter to send, Shift+Enter for newline)")
        self.setFixedHeight(80)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (e.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.submit_requested.emit()
            return
        super().keyPressEvent(e)


class AIPanel(QWidget):
    def __init__(self, engine, parent=None, command_handler=None):
        super().__init__(parent)
        self.engine = engine
        self.command_handler = command_handler
        self.worker = EngineWorker(engine, self)
        self._config = load_gui_chat_config()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("VIVIAN AI")
        header.setObjectName("aiHeader")
        layout.addWidget(header)

        mode_row = QWidget()
        mode_layout = QHBoxLayout(mode_row)
        mode_layout.setContentsMargins(6, 6, 6, 0)
        mode_layout.setSpacing(6)
        mode_label = QLabel("Mode")
        self.mode_combo = QComboBox()
        self.mode_combo.setToolTip("Choose how the AI should behave for this chat turn")
        self._reload_modes()
        self.reload_config_btn = QPushButton("Reload Config")
        self.open_config_btn = QPushButton("Open Config")
        self.reload_config_btn.clicked.connect(self._reload_config)
        self.open_config_btn.clicked.connect(self._open_config)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo, 1)
        mode_layout.addWidget(self.reload_config_btn)
        mode_layout.addWidget(self.open_config_btn)
        layout.addWidget(mode_row)

        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setAcceptRichText(False)
        layout.addWidget(self.transcript, 1)

        input_row = QWidget()
        input_layout = QVBoxLayout(input_row)
        input_layout.setContentsMargins(6, 6, 6, 6)
        input_layout.setSpacing(4)
        self.input = _ChatInput()
        input_layout.addWidget(self.input)

        btn_row = QHBoxLayout()
        self.include_cb = QCheckBox("Include open file")
        self.include_cb.setToolTip("Attach the currently open file's content to your message")
        self.include_cb.setEnabled(False)  # enabled when a file is active
        self.send_btn = QPushButton("Send")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        btn_row.addWidget(self.include_cb)
        btn_row.addStretch(1)
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.send_btn)
        input_layout.addLayout(btn_row)
        layout.addWidget(input_row)

        # Signals
        self.send_btn.clicked.connect(self._submit)
        self.input.submit_requested.connect(self._submit)
        self.stop_btn.clicked.connect(self.worker.interrupt)
        self.worker.chunk_ready.connect(self._on_chunk)
        self.worker.tool_result.connect(self._on_tool)
        self.worker.system_msg.connect(self._on_system)
        self.worker.error.connect(self._on_error)
        self.worker.command_output.connect(self._on_command_output)
        self.worker.done.connect(self._on_done)

        self._streaming = False
        self._active_file_path: Optional[str] = None
        self._active_file_content: Optional[str] = None
        self._append_intro("Vivian AI is ready. Type below to chat.\n")
        if bool((self._config.get("gui_settings") or {}).get("include_open_file_by_default")):
            self.include_cb.setChecked(True)

    def _reload_modes(self) -> None:
        current = getattr(self, "mode_combo", None)
        current_mode = None
        if current is not None:
            current_mode = current.currentData()
            current.blockSignals(True)
            current.clear()
        available_modes = self._config.get("available_modes") or []
        for mode in available_modes:
            if current is not None:
                current.addItem(mode.get("label", mode.get("id", "Mode")), mode.get("id"))
        default_mode = self._config.get("default_mode")
        target = current_mode if current_mode in {m.get("id") for m in available_modes} else default_mode
        if current is not None:
            idx = current.findData(target)
            current.setCurrentIndex(idx if idx >= 0 else 0)
            current.blockSignals(False)

    def _reload_config(self) -> None:
        self._config = load_gui_chat_config()
        self._reload_modes()
        self._append_intro(f"Reloaded chat config from {get_gui_chat_config_path()}\n")

    def _open_config(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(get_gui_chat_config_path())))

    def set_active_file(self, path: str, content: str) -> None:
        """Called by MainWindow when the editor's active tab changes."""
        self._active_file_path = path or None
        self._active_file_content = content if path else None
        self.include_cb.setEnabled(bool(path))
        if path:
            name = path.split("/")[-1].split("\\")[-1]
            self.include_cb.setText(f"Include: {name}")
            self.include_cb.setToolTip(path)
        else:
            self.include_cb.setText("Include open file")
            self.include_cb.setToolTip("Attach the currently open file's content to your message")
            self.include_cb.setChecked(False)

    # ---- UI helpers ------------------------------------------------------
    def _append_intro(self, text: str) -> None:
        self._append_styled(text, "#888888", italic=True)

    def _append_styled(self, text: str, color: str, bold: bool = False, italic: bool = False) -> None:
        cursor = self.transcript.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(700)
        if italic:
            fmt.setFontItalic(True)
        cursor.insertText(text, fmt)
        self.transcript.setTextCursor(cursor)
        sb = self.transcript.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _append_plain(self, text: str) -> None:
        self._append_styled(text, "#d4d4d4")

    # ---- Slots -----------------------------------------------------------
    def _submit(self) -> None:
        if self._streaming:
            return
        text = self.input.toPlainText().strip()
        if not text:
            return
        self.input.clear()

        if text.startswith("/") and self.command_handler is not None:
            self._append_styled("\nYou: ", "#4ec9b0", bold=True)
            self._append_plain(text + "\n")
            self._append_styled("\nCommand: ", "#dcdcaa", bold=True)
            self._streaming = True
            self.send_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.worker.submit_command(text[1:], self.command_handler)
            return

        # Append file context if the checkbox is checked and we have a file
        prompt = text
        file_label = ""
        if (self.include_cb.isChecked()
                and self._active_file_path
                and self._active_file_content is not None):
            ext = self._active_file_path.rsplit(".", 1)[-1] if "." in self._active_file_path else "text"
            name = self._active_file_path.split("/")[-1].split("\\")[-1]
            file_label = f"  [+ {name}]"
            prompt = (
                f"{text}\n\n"
                f"Open file — {name}:\n"
                f"```{ext}\n{self._active_file_content}\n```"
            )

        self._append_styled("\nYou: ", "#4ec9b0", bold=True)
        self._append_plain(text + file_label + "\n")
        self._append_styled("\nVivian: ", "#569cd6", bold=True)
        self._streaming = True
        self.send_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        mode_prompt = compose_mode_prompt(
            prompt,
            self.mode_combo.currentData(),
            is_employee=bool(self._config.get("is_employee")),
            expose_internal_modes=bool((self._config.get("user_settings") or {}).get("show_internal_modes")),
        )
        self.worker.submit(prompt, mode_prompt=mode_prompt)

    def _on_chunk(self, chunk: str) -> None:
        self._append_plain(chunk)

    def _on_tool(self, tool_name: str, result: dict) -> None:
        self._append_styled(f"\n  ⚙ {tool_name}\n", "#888888", italic=True)
        if not isinstance(result, dict):
            self._append_plain(str(result)[:4000] + "\n")
            return
        if result.get("error"):
            self._append_styled(f"  ✗ {result['error']}\n", "#f48771")
            return
        stdout = result.get("stdout") or ""
        stderr = result.get("stderr") or ""
        if stdout:
            self._append_plain(stdout.rstrip("\n") + "\n")
        if stderr:
            self._append_styled(stderr.rstrip("\n") + "\n", "#f48771")
        if not stdout and not stderr:
            fb = result.get("content") or result.get("output") or ""
            if isinstance(fb, (list, tuple)):
                fb = "\n".join(str(x) for x in fb)
            fb = str(fb).strip()
            if fb:
                self._append_plain(fb[:4000] + "\n")

    def _on_system(self, msg: str) -> None:
        self._append_styled(f"\n[{msg}]\n", "#dcdcaa", italic=True)

    def _on_error(self, err: str) -> None:
        self._append_styled(f"\nError: {err}\n", "#f48771")

    def _on_done(self) -> None:
        self._append_plain("\n")
        self._streaming = False
        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _on_command_output(self, text: str) -> None:
        self._append_plain(text.rstrip("\n") + "\n")

    def shutdown(self) -> None:
        self.worker.shutdown()

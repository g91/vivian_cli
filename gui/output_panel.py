"""Bottom dock that streams build / flash / monitor output and can send input."""
from __future__ import annotations
import re
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeyEvent, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QDockWidget, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton,
    QVBoxLayout, QWidget,
)


_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


class _MonitorInput(QLineEdit):
    sent = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Monitor input — Enter sends a line, Ctrl+] exits monitor")
        self.returnPressed.connect(self._submit)

    def _submit(self) -> None:
        text = self.text()
        self.clear()
        self.sent.emit(text + "\n")

    def keyPressEvent(self, e: QKeyEvent) -> None:
        # Ctrl+] is the ESP-IDF monitor exit key
        if e.key() == Qt.Key.Key_BracketRight and (e.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.sent.emit("\x1d")
            return
        super().keyPressEvent(e)


class OutputPanel(QDockWidget):
    monitor_input = pyqtSignal(str)
    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Output", parent)
        self.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header row (description + clear/stop buttons)
        header_row = QWidget()
        hl = QHBoxLayout(header_row)
        hl.setContentsMargins(8, 4, 8, 4)
        hl.setSpacing(6)
        self.title_label = QLabel("OUTPUT")
        self.title_label.setStyleSheet("color: #bbbbbb; font-size: 11px; font-weight: 600;")
        hl.addWidget(self.title_label)
        hl.addStretch(1)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(lambda: self.text.clear())
        hl.addWidget(self.clear_btn)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        hl.addWidget(self.stop_btn)
        layout.addWidget(header_row)

        # Output area
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setMaximumBlockCount(8000)
        mono = QFont("Cascadia Code")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        mono.setPointSize(11)
        self.text.setFont(mono)
        layout.addWidget(self.text, 1)

        # Monitor input row (hidden unless in monitor mode)
        self.input = _MonitorInput()
        self.input.sent.connect(self.monitor_input.emit)
        self.input.setVisible(False)
        layout.addWidget(self.input)

        self.setWidget(body)
        self.resize(self.width(), 240)

    def append(self, text: str) -> None:
        clean = _strip_ansi(text)
        cursor = self.text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        # Faintly color stderr-ish [exit N] markers and our own [runner] lines
        if clean.startswith("[exit ") or clean.startswith("[runner") or clean.startswith("[build]") or clean.startswith("[flash]") or clean.startswith("[monitor]"):
            fmt.setForeground(QColor("#dcdcaa"))
        cursor.insertText(clean, fmt)
        self.text.setTextCursor(cursor)
        sb = self.text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def set_running(self, running: bool, description: str = "") -> None:
        self.stop_btn.setEnabled(running)
        if running and description:
            self.title_label.setText(f"OUTPUT — {description}")
        elif not running:
            self.title_label.setText("OUTPUT")

    def set_monitor_mode(self, on: bool) -> None:
        self.input.setVisible(on)
        if on:
            self.input.setFocus()

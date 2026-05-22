"""Run & Debug panel — runs the executable produced by the build, or executes
interpreted scripts directly. Output streams into the shared output dock."""
from __future__ import annotations
import os
import shutil
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton, QVBoxLayout,
    QWidget,
)


_RUN_FOR_EXT = {
    ".py":  ("python", lambda f: ["python3", f]),
    ".js":  ("node",   lambda f: ["node", f]),
    ".mjs": ("node",   lambda f: ["node", f]),
    ".ts":  ("ts-node", lambda f: ["ts-node", f]),
    ".sh":  ("bash",   lambda f: ["bash", f]),
    ".rb":  ("ruby",   lambda f: ["ruby", f]),
    ".php": ("php",    lambda f: ["php", f]),
    ".lua": ("lua",    lambda f: ["lua", f]),
}


def runner_for_file(path: str) -> Optional[tuple[str, list[str]]]:
    """Return (label, argv) for running an interpreted script directly."""
    if not path:
        return None
    ext = os.path.splitext(path)[1].lower()
    hit = _RUN_FOR_EXT.get(ext)
    if not hit:
        return None
    label, builder = hit
    return label, builder(path)


def binary_for_file(path: str) -> Optional[tuple[str, list[str]]]:
    """For compiled languages, prefer the binary next to the source."""
    if not path:
        return None
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".c", ".cpp", ".cc", ".cxx", ".rs", ".go"):
        return None
    stem = os.path.splitext(path)[0]
    if os.path.isfile(stem) and os.access(stem, os.X_OK):
        return os.path.basename(stem), [stem]
    return None


class RunPanel(QWidget):
    """Emit run_command([argv], description) for MainWindow to dispatch."""
    run_command = pyqtSignal(list, str)
    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_file = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("RUN AND DEBUG")
        header.setObjectName("explorerHeader")
        layout.addWidget(header)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(10, 8, 10, 8)
        bl.setSpacing(6)

        self.target_label = QLabel("No runnable target")
        self.target_label.setStyleSheet("color: #cccccc;")
        self.target_label.setWordWrap(True)
        bl.addWidget(self.target_label)

        mode_label = QLabel("Source")
        mode_label.setStyleSheet("color: #858585; font-size: 11px;")
        bl.addWidget(mode_label)
        self.mode_script = QRadioButton("Run the script directly (interpreted)")
        self.mode_binary = QRadioButton("Run compiled binary (./stem)")
        self.mode_custom = QRadioButton("Custom command:")
        self.mode_script.setChecked(True)
        for rb in (self.mode_script, self.mode_binary, self.mode_custom):
            rb.toggled.connect(lambda _c=False: self._refresh_target())
            bl.addWidget(rb)

        self.custom_edit = QLineEdit()
        self.custom_edit.setPlaceholderText('e.g. python3 -m myapp --debug')
        self.custom_edit.setEnabled(False)
        self.mode_custom.toggled.connect(self.custom_edit.setEnabled)
        bl.addWidget(self.custom_edit)

        args_label = QLabel("Arguments")
        args_label.setStyleSheet("color: #858585; font-size: 11px;")
        bl.addWidget(args_label)
        self.args_edit = QLineEdit()
        self.args_edit.setPlaceholderText("(optional) program arguments")
        bl.addWidget(self.args_edit)

        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("▶ Run")
        self.run_btn.clicked.connect(self._run)
        btn_row.addWidget(self.run_btn)
        self.stop_btn = QPushButton("◼ Stop")
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        btn_row.addWidget(self.stop_btn)
        btn_row.addStretch(1)
        bl.addLayout(btn_row)

        bl.addStretch(1)
        layout.addWidget(body, 1)

        self.set_current_file("")

    # ── public ────────────────────────────────────────────────────────────
    def set_current_file(self, path: str) -> None:
        self._current_file = path
        self._refresh_target()

    # ── internals ─────────────────────────────────────────────────────────
    def _refresh_target(self) -> None:
        script = runner_for_file(self._current_file)
        binary = binary_for_file(self._current_file)
        self.mode_script.setEnabled(script is not None)
        self.mode_binary.setEnabled(binary is not None)
        if self.mode_script.isChecked() and script:
            self.target_label.setText(f"Will run:  {' '.join(script[1])}")
        elif self.mode_binary.isChecked() and binary:
            self.target_label.setText(f"Will run:  {' '.join(binary[1])}")
        elif self.mode_custom.isChecked():
            cmd = self.custom_edit.text().strip()
            self.target_label.setText(f"Will run:  {cmd or '(enter a command above)'}")
        else:
            # Fall back to whatever is available
            if script:
                self.mode_script.setChecked(True)
            elif binary:
                self.mode_binary.setChecked(True)
            else:
                self.target_label.setText("No runnable target for this file. Pick Custom or open a .py/.js/.sh/etc. file.")

    def _run(self) -> None:
        argv: list[str] = []
        desc = ""
        if self.mode_custom.isChecked():
            cmd = self.custom_edit.text().strip()
            if not cmd:
                self.target_label.setText("Enter a command above first.")
                return
            argv = cmd.split()
            desc = f"custom: {cmd}"
        elif self.mode_binary.isChecked():
            binary = binary_for_file(self._current_file)
            if not binary:
                self.target_label.setText("No binary found next to the source — build first.")
                return
            argv = binary[1][:]
            desc = f"run binary: {os.path.basename(binary[1][0])}"
        else:  # script
            script = runner_for_file(self._current_file)
            if not script:
                self.target_label.setText("This file isn't directly runnable. Try Custom.")
                return
            argv = script[1][:]
            if not shutil.which(argv[0]):
                self.target_label.setText(f"'{argv[0]}' not found on PATH.")
                return
            desc = f"run script: {os.path.basename(self._current_file)}"

        extra = self.args_edit.text().strip()
        if extra:
            argv += extra.split()

        self.run_command.emit(argv, desc)

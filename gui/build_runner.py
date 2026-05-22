"""Build / flash / monitor backend.

Wraps QProcess so the UI can stream output line-by-line and send input back
to a running monitor. Pure-Python detection helpers live in build_detect so
the web GUI can use them without importing Qt.
"""
from __future__ import annotations
import os
import shutil
from typing import Optional

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, pyqtSignal

# Re-export so existing callers keep working
from .build_detect import (ProjectKind, compiler_for_file, detect_project,
                           is_esp_idf_project)  # noqa: F401


class BuildRunner(QObject):
    """Runs builds / flashes / monitors as a QProcess and streams output."""

    output = pyqtSignal(str)        # raw stdout/stderr line
    started = pyqtSignal(str)       # human-readable description
    finished = pyqtSignal(int)      # exit code (0 = success)
    state_changed = pyqtSignal(bool)  # True = running

    def __init__(self, parent=None):
        super().__init__(parent)
        self.proc: Optional[QProcess] = None
        self.project_root: str = os.getcwd()
        self.target: str = "esp32"
        self.last_command: str = ""

    # ── public API ──────────────────────────────────────────────────────
    def set_root(self, root: str) -> None:
        self.project_root = root

    def set_target(self, target: str) -> None:
        self.target = target

    def is_running(self) -> bool:
        return self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning

    def build(self, current_file: str = "") -> None:
        # ESP-IDF and Make win over per-file recipes — those are project builds.
        if is_esp_idf_project(self.project_root):
            self._spawn("idf.py", ["-DIDF_TARGET=" + self.target, "build"], "ESP-IDF build")
            return
        try:
            entries = set(os.listdir(self.project_root))
        except OSError:
            entries = set()
        if "Makefile" in entries or "makefile" in entries or "GNUmakefile" in entries:
            self._spawn("make", [], "make")
            return
        # Per-file recipe based on current editor language.
        recipe = compiler_for_file(current_file) if current_file else None
        if recipe:
            argv = recipe["argv"]
            self._spawn(argv[0], argv[1:], recipe["label"])
            return
        self.output.emit(
            "[build] Nothing to build — open a source file (.c/.cpp/.cs/.rs/.go/.java/.ts/…) "
            "or open a project with a Makefile or ESP-IDF config.\n"
        )

    def flash(self, method: str = "uart", current_file: str = "") -> None:
        kind = detect_project(self.project_root, current_file)
        if kind is not ProjectKind.ESP_IDF:
            self.output.emit("[flash] Flashing is only wired for ESP-IDF projects right now.\n")
            return
        args = ["-DIDF_TARGET=" + self.target]
        if method == "jtag":
            args += ["openocd", "flash"]
            desc = "ESP-IDF flash (JTAG / OpenOCD)"
        elif method == "dfu":
            args += ["dfu-flash"]
            desc = "ESP-IDF flash (DFU)"
        else:
            args += ["flash"]
            desc = "ESP-IDF flash (UART)"
        self._spawn("idf.py", args, desc)

    def monitor(self, current_file: str = "") -> None:
        kind = detect_project(self.project_root, current_file)
        if kind is not ProjectKind.ESP_IDF:
            self.output.emit("[monitor] Monitor is wired for ESP-IDF projects.\n")
            return
        self._spawn("idf.py", ["-DIDF_TARGET=" + self.target, "monitor"], "ESP-IDF monitor")

    def stop(self) -> None:
        if self.proc and self.proc.state() != QProcess.ProcessState.NotRunning:
            self.proc.terminate()
            if not self.proc.waitForFinished(2000):
                self.proc.kill()

    def send_input(self, data: str) -> None:
        """Forward keystrokes to the monitor stdin."""
        if self.proc and self.proc.state() == QProcess.ProcessState.Running:
            self.proc.write(data.encode("utf-8", errors="replace"))

    # ── internals ───────────────────────────────────────────────────────
    def _build_single(self, source: str, cpp: bool) -> None:
        exe = "g++" if cpp else "gcc"
        if not shutil.which(exe):
            self.output.emit(f"[build] {exe} not found on PATH.\n")
            return
        out_path = os.path.splitext(source)[0]
        self._spawn(exe, [source, "-o", out_path, "-Wall"], f"{exe} {os.path.basename(source)}")

    def _spawn(self, program: str, args: list[str], description: str) -> None:
        if self.is_running():
            self.output.emit("[runner] A process is already running. Stop it first.\n")
            return

        if not shutil.which(program):
            hint = ""
            if program == "idf.py":
                hint = (" — source $IDF_PATH/export.sh or run from an ESP-IDF terminal "
                        "so idf.py is on PATH.")
            self.output.emit(f"[runner] '{program}' not found on PATH.{hint}\n")
            return

        self.proc = QProcess(self)
        self.proc.setWorkingDirectory(self.project_root)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        env = QProcessEnvironment.systemEnvironment()
        # Force colour output where supported so the ESP-IDF banner stays readable.
        env.insert("CLICOLOR_FORCE", "1")
        env.insert("PYTHONUNBUFFERED", "1")
        self.proc.setProcessEnvironment(env)

        self.proc.readyReadStandardOutput.connect(self._on_output)
        self.proc.finished.connect(self._on_finished)
        self.proc.errorOccurred.connect(self._on_error)

        self.last_command = " ".join([program, *args])
        self.output.emit(f"\n$ {self.last_command}\n  (in {self.project_root})\n")
        self.started.emit(description)
        self.state_changed.emit(True)
        self.proc.start(program, args)

    def _on_output(self) -> None:
        if not self.proc:
            return
        data = bytes(self.proc.readAllStandardOutput())
        if data:
            self.output.emit(data.decode("utf-8", errors="replace"))

    def _on_finished(self, exit_code: int, _status) -> None:
        self.output.emit(f"\n[exit {exit_code}]\n")
        self.finished.emit(exit_code)
        self.state_changed.emit(False)
        self.proc = None

    def _on_error(self, err) -> None:
        self.output.emit(f"[runner error] {err}\n")

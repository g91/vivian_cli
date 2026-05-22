"""Main IDE window — VS Code-style layout.

Left to right:
  ActivityBar | Sidebar (stacked) | Editor area (welcome / tabs) | AI panel
"""
from __future__ import annotations
import os
from typing import Callable, Optional
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout,
    QLabel, QMainWindow, QSpinBox, QSplitter, QStackedWidget, QStatusBar,
    QVBoxLayout, QWidget,
)

from .activity_bar import ActivityBar
from .ai_panel import AIPanel
from .build_runner import BuildRunner, compiler_for_file, is_esp_idf_project
from .editor_tabs import EditorTabs
from .esp_status import ESPStatus
from .file_explorer import FileExplorer
from .output_panel import OutputPanel
from .plugin_api import PluginAPI
from .sidebar_extensions import ExtensionsPanel
from .sidebar_run import RunPanel
from .sidebar_scm import SCMPanel
from .sidebar_search import SearchPanel
from .welcome import WelcomePage


class _StubPanel(QWidget):
    """Placeholder for sidebar pages we haven't fully implemented yet."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QLabel(title.upper())
        header.setObjectName("explorerHeader")
        layout.addWidget(header)
        body = QLabel(f"\n  {title} — coming soon.\n")
        body.setStyleSheet("color: #858585;")
        body.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(body, 1)


class SettingsDialog(QDialog):
    def __init__(self, parent=None, current_font_size: int = 13):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(320)
        layout = QFormLayout(self)
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 32)
        self.font_size.setValue(current_font_size)
        layout.addRow("Editor font size:", self.font_size)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class IDEWindow(QMainWindow):
    def __init__(self, engine, initial_path: str = "", command_handler: Optional[Callable] = None):
        super().__init__()
        self.engine = engine
        self.command_handler = command_handler
        self.setWindowTitle("Vivian IDE")
        self.resize(1400, 900)
        self._editor_font_size = 13

        # Resolve initial folder
        initial_folder = initial_path or os.getcwd()
        if os.path.isfile(initial_folder):
            initial_folder = os.path.dirname(initial_folder)

        # ---- activity bar -------------------------------------------------
        self.activity = ActivityBar()

        # ---- plugin API (must exist before ExtensionsPanel is built) ------
        self.plugin_api = PluginAPI(self)

        # ---- sidebar stack (Explorer / Search / SCM / Run / Extensions) ---
        self.sidebar = QStackedWidget()
        self.sidebar.setMinimumWidth(220)
        self.explorer = FileExplorer(initial_folder)
        self.search_panel = SearchPanel(initial_folder)
        self.scm_panel = SCMPanel(initial_folder)
        self.run_panel = RunPanel()
        self.extensions_panel = ExtensionsPanel(self.plugin_api)
        self.sidebar.addWidget(self.explorer)         # 0
        self.sidebar.addWidget(self.search_panel)     # 1
        self.sidebar.addWidget(self.scm_panel)        # 2
        self.sidebar.addWidget(self.run_panel)        # 3
        self.sidebar.addWidget(self.extensions_panel) # 4
        self._sidebar_index = {
            "explorer": 0, "search": 1, "scm": 2, "run": 3, "extensions": 4,
        }

        # ---- editor area: welcome ↔ tabs ---------------------------------
        self.editor_stack = QStackedWidget()
        self.welcome = WelcomePage()
        self.tabs = EditorTabs()
        self.editor_stack.addWidget(self.welcome)   # 0
        self.editor_stack.addWidget(self.tabs)      # 1
        self.tabs.tab_count_changed.connect(lambda _n: self._sync_editor_view())
        # Welcome links
        self.welcome.new_file_clicked.connect(self.tabs.new_untitled)
        self.welcome.open_file_clicked.connect(self._open_file_dialog)
        self.welcome.open_folder_clicked.connect(self._open_folder_dialog)

        # ---- AI panel -----------------------------------------------------
        self.ai = AIPanel(engine, command_handler=self.command_handler)

        # ---- layout: activity | sidebar | (editor | ai) ------------------
        center_splitter = QSplitter(Qt.Orientation.Horizontal)
        center_splitter.addWidget(self.editor_stack)
        center_splitter.addWidget(self.ai)
        center_splitter.setStretchFactor(0, 3)
        center_splitter.setStretchFactor(1, 1)
        center_splitter.setSizes([900, 400])

        side_splitter = QSplitter(Qt.Orientation.Horizontal)
        side_splitter.addWidget(self.sidebar)
        side_splitter.addWidget(center_splitter)
        side_splitter.setStretchFactor(0, 0)
        side_splitter.setStretchFactor(1, 1)
        side_splitter.setSizes([240, 1160])

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self.activity)
        root_layout.addWidget(side_splitter, 1)
        self.setCentralWidget(root)

        # ---- build / flash / monitor runner + output dock -----------------
        self.runner = BuildRunner(self)
        self.runner.set_root(initial_folder)
        self.output_dock = OutputPanel(self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.output_dock)
        self.output_dock.hide()  # Show on first build/flash/monitor invocation

        # ---- status bar ---------------------------------------------------
        self._build_status_bar(initial_folder)

        # ---- wiring -------------------------------------------------------
        self.activity.page_selected.connect(self._switch_sidebar)
        self.activity.settings_requested.connect(self._open_settings)
        self.explorer.file_opened.connect(self.tabs.open_file)
        self.explorer.root_changed.connect(self._on_root_changed)
        self.tabs.cursor_changed.connect(self._on_cursor)

        # Build runner wiring
        self.esp_status.target_changed.connect(self.runner.set_target)
        self.esp_status.build_requested.connect(self._do_build)
        self.esp_status.flash_requested.connect(self._do_flash)
        self.esp_status.monitor_requested.connect(self._do_monitor)
        self.esp_status.stop_requested.connect(self.runner.stop)
        self.runner.output.connect(self.output_dock.append)
        self.runner.started.connect(self._on_runner_started)
        self.runner.finished.connect(self._on_runner_finished)
        self.runner.state_changed.connect(self.esp_status.set_running)
        self.runner.state_changed.connect(
            lambda r: self.output_dock.set_running(r, self.runner.last_command)
        )
        self.output_dock.stop_requested.connect(self.runner.stop)
        self.output_dock.monitor_input.connect(self.runner.send_input)
        # Sync initial target to runner
        self.runner.set_target(self.esp_status.current_target())

        # Context-sensitive build controls: refresh whenever the root or active
        # file changes (so ESP toolbar appears/hides and Build label tracks the
        # current compiler).
        self.tabs.current_file_changed.connect(lambda _p: self._refresh_build_controls())
        self.tabs.tab_count_changed.connect(lambda _n: self._refresh_build_controls())
        self._refresh_build_controls()

        # ---- sidebar panel wiring ----------------------------------------
        # Search → jump to result
        self.search_panel.open_at.connect(self._open_at_line)
        # SCM → dispatch git commands through the runner / output dock
        self.scm_panel.run_git_command.connect(self._run_git)
        # Run panel → use the runner / output dock
        self.run_panel.run_command.connect(self._run_arbitrary)
        self.run_panel.stop_requested.connect(self.runner.stop)
        # Keep Run panel in sync with current file
        self.tabs.current_file_changed.connect(self.run_panel.set_current_file)
        # Notify AI panel when active file changes so the "Include open file"
        # checkbox can show the right filename and read its content
        self.tabs.current_file_changed.connect(self._sync_ai_active_file)
        # Plugin events: notify on file open and save
        self.tabs.current_file_changed.connect(
            lambda p: self.plugin_api.fire_file_opened(p) if p else None
        )
        self.tabs.file_saved.connect(self.plugin_api.fire_file_saved)

        # Menu
        self._build_menu()

        # Initial open
        if initial_path and os.path.isfile(initial_path):
            self.tabs.open_file(initial_path)
        self._sync_editor_view()

    # ---- sidebar -------------------------------------------------------
    def _switch_sidebar(self, page_id: str) -> None:
        idx = self._sidebar_index.get(page_id)
        if idx is None:
            return
        # If clicking the active item, toggle visibility (VS Code behavior)
        if self.sidebar.isVisible() and self.sidebar.currentIndex() == idx:
            self.sidebar.setVisible(False)
            return
        self.sidebar.setVisible(True)
        self.sidebar.setCurrentIndex(idx)

    def _sync_editor_view(self) -> None:
        self.editor_stack.setCurrentIndex(1 if self.tabs.count() > 0 else 0)

    def _sync_ai_active_file(self, path: str) -> None:
        """Forward the current file path + content to the AI panel."""
        if path:
            ed = self.tabs.currentWidget()
            content = ed.toPlainText() if ed is not None else ""
            self.ai.set_active_file(path, content)
        else:
            self.ai.set_active_file("", "")

    # ---- status bar ----------------------------------------------------
    def _build_status_bar(self, cwd: str) -> None:
        bar = QStatusBar()
        bar.setSizeGripEnabled(False)
        self.setStatusBar(bar)

        self.branch_label = QLabel("⎇ main")
        self.problems_label = QLabel("ⓧ 0  ⚠ 0")
        self.cwd_label = QLabel(cwd)
        self.cursor_label = QLabel("Ln 1, Col 1")
        self.encoding_label = QLabel("UTF-8")
        self.eol_label = QLabel("LF")
        self.indent_label = QLabel("Spaces: 4")
        self.lang_label = QLabel("text")
        self.esp_status = ESPStatus()

        for w in (self.branch_label, self.problems_label):
            bar.addWidget(w)
        bar.addWidget(QLabel(), 1)  # spacer
        # ESP-IDF controls sit to the LEFT of the cursor/lang segments
        bar.addPermanentWidget(self.esp_status)
        for w in (self.cursor_label, self.indent_label, self.encoding_label,
                  self.eol_label, self.lang_label):
            bar.addPermanentWidget(w)

    # ---- menu ----------------------------------------------------------
    def _build_menu(self) -> None:
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        self._add(file_menu, "New File", "Ctrl+N", self.tabs.new_untitled)
        self._add(file_menu, "Open File…", "Ctrl+O", self._open_file_dialog)
        self._add(file_menu, "Open Folder…", "Ctrl+K Ctrl+O", self._open_folder_dialog)
        file_menu.addSeparator()
        self._add(file_menu, "Save", "Ctrl+S", self.tabs.save_current)
        self._add(file_menu, "Save As…", "Ctrl+Shift+S", self.tabs.save_current_as)
        file_menu.addSeparator()
        self._add(file_menu, "Close Tab", "Ctrl+W", self._close_current_tab)
        self._add(file_menu, "Exit", "Ctrl+Q", self.close)

        edit_menu = menubar.addMenu("&Edit")
        self._add(edit_menu, "Undo", QKeySequence.StandardKey.Undo, lambda: self._editor_action("undo"))
        self._add(edit_menu, "Redo", QKeySequence.StandardKey.Redo, lambda: self._editor_action("redo"))
        edit_menu.addSeparator()
        self._add(edit_menu, "Cut", QKeySequence.StandardKey.Cut, lambda: self._editor_action("cut"))
        self._add(edit_menu, "Copy", QKeySequence.StandardKey.Copy, lambda: self._editor_action("copy"))
        self._add(edit_menu, "Paste", QKeySequence.StandardKey.Paste, lambda: self._editor_action("paste"))

        view_menu = menubar.addMenu("&View")
        self._add(view_menu, "Toggle Explorer", "Ctrl+B",
                  lambda: self.sidebar.setVisible(not self.sidebar.isVisible()))
        self._add(view_menu, "Toggle AI Panel", "Ctrl+Shift+A",
                  lambda: self.ai.setVisible(not self.ai.isVisible()))
        view_menu.addSeparator()
        self._add(view_menu, "Settings…", "Ctrl+,", self._open_settings)

        help_menu = menubar.addMenu("&Help")
        self._add(help_menu, "About Vivian IDE", "", self._about)

    def _add(self, menu, label, shortcut, slot) -> None:
        act = QAction(label, self)
        if shortcut:
            if isinstance(shortcut, str):
                act.setShortcut(QKeySequence(shortcut))
            else:
                act.setShortcut(shortcut)
        act.triggered.connect(lambda checked=False: slot())
        menu.addAction(act)

    # ---- slots ---------------------------------------------------------
    def _open_file_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open File", os.getcwd())
        if path:
            self.tabs.open_file(path)

    def _open_folder_dialog(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Open Folder", os.getcwd())
        if path:
            self.explorer.set_root(path)

    def _close_current_tab(self) -> None:
        idx = self.tabs.currentIndex()
        if idx >= 0:
            self.tabs._close_tab(idx)

    def _editor_action(self, action: str) -> None:
        ed = self.tabs.currentWidget()
        if ed is None:
            return
        getattr(ed, action, lambda: None)()

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self, self._editor_font_size)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._editor_font_size = dlg.font_size.value()
            for i in range(self.tabs.count()):
                ed = self.tabs.widget(i)
                f = ed.font()
                f.setPointSize(self._editor_font_size)
                ed.setFont(f)

    def _about(self) -> None:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.about(
            self, "About Vivian IDE",
            "<b>Vivian IDE</b><br>Qt-based editor that talks to Vivian CLI.<br>"
            "Folder tree, tabbed editor, AI chat — all in one window.",
        )

    def _on_root_changed(self, path: str) -> None:
        self.cwd_label.setText(path)
        try:
            os.chdir(path)
            self.engine.cwd = path
        except OSError:
            pass
        self.runner.set_root(path)
        self.search_panel.set_root(path)
        self.scm_panel.set_root(path)
        self._refresh_branch(path)
        self._refresh_build_controls()

    # ---- helpers used by the new sidebar panels ------------------------
    def _open_at_line(self, path: str, line: int) -> None:
        ed = self.tabs.open_file(path)
        if ed is None:
            return
        from PyQt6.QtGui import QTextCursor
        cursor = ed.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        for _ in range(max(0, line - 1)):
            cursor.movePosition(QTextCursor.MoveOperation.Down)
        ed.setTextCursor(cursor)
        ed.centerCursor()
        ed.setFocus()

    def _run_git(self, args: list, description: str) -> None:
        # Dispatch git through the runner + output dock; refresh SCM on finish.
        self._show_output()
        self.output_dock.set_monitor_mode(False)
        # One-shot connection: when this run finishes, refresh the SCM view.
        def _on_done(_code, _scm=self.scm_panel):
            self.runner.finished.disconnect(_on_done)
            _scm.refresh()
        self.runner.finished.connect(_on_done)
        self.runner._spawn("git", ["-C", self.runner.project_root, *args], description)

    def _run_arbitrary(self, argv: list, description: str) -> None:
        if not argv:
            return
        self._show_output()
        self.output_dock.set_monitor_mode(False)
        self.runner._spawn(argv[0], list(argv[1:]), description)

    def _refresh_build_controls(self) -> None:
        """Show ESP controls only for IDF projects; otherwise label Build with
        the compiler that fits the currently-open file."""
        is_esp = is_esp_idf_project(self.runner.project_root)
        self.esp_status.set_esp_mode(is_esp)

        if is_esp:
            self.esp_status.set_compiler_label("Build")
            self.esp_status.set_build_visible(True)
            return

        # Non-ESP: try to pick a compiler from the active file
        current = self._current_file()
        # Project-level builds beat per-file recipes
        try:
            entries = set(os.listdir(self.runner.project_root))
        except OSError:
            entries = set()
        has_make = any(n in entries for n in ("Makefile", "makefile", "GNUmakefile"))
        if has_make:
            self.esp_status.set_compiler_label("make")
            self.esp_status.set_build_visible(True)
            return

        recipe = compiler_for_file(current) if current else None
        if recipe:
            self.esp_status.set_compiler_label(recipe["label"])
            self.esp_status.set_build_visible(True)
        else:
            # Nothing to build for this file — hide the button entirely
            self.esp_status.set_build_visible(False)

    def _current_file(self) -> str:
        ed = self.tabs.currentWidget()
        return getattr(ed, "file_path", "") if ed else ""

    def _show_output(self) -> None:
        if not self.output_dock.isVisible():
            self.output_dock.show()
            self.output_dock.raise_()

    def _do_build(self) -> None:
        self._show_output()
        self.output_dock.set_monitor_mode(False)
        self.runner.build(self._current_file())

    def _do_flash(self, method: str) -> None:
        self._show_output()
        self.output_dock.set_monitor_mode(False)
        self.runner.flash(method, self._current_file())

    def _do_monitor(self) -> None:
        self._show_output()
        self.output_dock.set_monitor_mode(True)
        self.runner.monitor(self._current_file())

    def _on_runner_started(self, description: str) -> None:
        self.statusBar().showMessage(f"Running: {description}", 4000)

    def _on_runner_finished(self, exit_code: int) -> None:
        msg = "Build succeeded" if exit_code == 0 else f"Build failed (exit {exit_code})"
        self.statusBar().showMessage(msg, 6000)
        # Leave monitor mode after the process exits
        self.output_dock.set_monitor_mode(False)

    def _refresh_branch(self, path: str) -> None:
        import subprocess
        try:
            r = subprocess.run(
                ["git", "-C", path, "branch", "--show-current"],
                capture_output=True, text=True, timeout=2,
            )
            branch = (r.stdout or "").strip()
            self.branch_label.setText(f"⎇ {branch}" if branch else "⎇ —")
        except Exception:
            self.branch_label.setText("⎇ —")

    def _on_cursor(self, line: int, col: int, language: str) -> None:
        self.cursor_label.setText(f"Ln {line}, Col {col}")
        self.lang_label.setText(language or "text")

    def closeEvent(self, event) -> None:
        for i in range(self.tabs.count() - 1, -1, -1):
            ed = self.tabs.widget(i)
            if ed and ed.document().isModified():
                self.tabs.setCurrentIndex(i)
                self.tabs._close_tab(i)
                if self.tabs.indexOf(ed) >= 0:
                    event.ignore()
                    return
        self.ai.shutdown()
        super().closeEvent(event)

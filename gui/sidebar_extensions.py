"""Extensions sidebar — list installed plugins, enable/disable, open folder."""
from __future__ import annotations
import os
import subprocess
import sys

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from .plugin_api import (PLUGIN_DIR, PluginInfo, discover_plugins,
                         ensure_example_plugin, load_plugin, save_state,
                         unload_plugin)


class ExtensionsPanel(QWidget):
    """Manages plugin lifecycle. The MainWindow owns the PluginAPI instance."""

    def __init__(self, api, parent=None):
        super().__init__(parent)
        self._api = api
        self._plugins: list[PluginInfo] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("EXTENSIONS")
        header.setObjectName("explorerHeader")
        layout.addWidget(header)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(10, 8, 10, 8)
        bl.setSpacing(6)

        intro = QLabel(
            f"Plugins are .py files in:\n{PLUGIN_DIR}\nEach defines a register(api) function."
        )
        intro.setStyleSheet("color: #858585; font-size: 11px;")
        intro.setWordWrap(True)
        bl.addWidget(intro)

        btn_row = QHBoxLayout()
        self.reload_btn = QPushButton("Reload")
        self.reload_btn.clicked.connect(self.reload_plugins)
        btn_row.addWidget(self.reload_btn)
        self.folder_btn = QPushButton("Open folder")
        self.folder_btn.clicked.connect(self._open_folder)
        btn_row.addWidget(self.folder_btn)
        btn_row.addStretch(1)
        bl.addLayout(btn_row)

        layout.addWidget(body)

        self.list = QListWidget()
        self.list.itemChanged.connect(self._on_toggle)
        self.list.itemActivated.connect(self._show_details)
        layout.addWidget(self.list, 1)

        ensure_example_plugin()
        self.reload_plugins()

    # ── public ──────────────────────────────────────────────────────────
    def reload_plugins(self) -> None:
        # Unload everything first
        for p in self._plugins:
            if p.module is not None:
                unload_plugin(p, self._api)
        self._plugins = discover_plugins()
        # Auto-load enabled plugins
        for p in self._plugins:
            if p.enabled:
                load_plugin(p, self._api)
        self._refresh_list()

    # ── internals ──────────────────────────────────────────────────────
    def _refresh_list(self) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for p in self._plugins:
            text = p.name
            if p.description:
                text += f"  ·  {p.description}"
            if p.error:
                text += "  ·  ⚠ error (double-click to see)"
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if p.enabled else Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, p.name)
            if p.error:
                item.setForeground(Qt.GlobalColor.red)
            self.list.addItem(item)
        self.list.blockSignals(False)

    def _find_plugin(self, name: str) -> PluginInfo | None:
        for p in self._plugins:
            if p.name == name:
                return p
        return None

    def _on_toggle(self, item: QListWidgetItem) -> None:
        name = item.data(Qt.ItemDataRole.UserRole)
        p = self._find_plugin(name)
        if not p:
            return
        want_enabled = item.checkState() == Qt.CheckState.Checked
        if want_enabled == p.enabled and p.module is not None:
            return
        if want_enabled:
            load_plugin(p, self._api)
            if p.error:
                QMessageBox.warning(self, f"Plugin {p.name} failed", p.error)
                p.enabled = False
                item.setCheckState(Qt.CheckState.Unchecked)
                return
            p.enabled = True
        else:
            unload_plugin(p, self._api)
            p.enabled = False
        save_state(self._plugins)
        self._refresh_list()

    def _show_details(self, item: QListWidgetItem) -> None:
        name = item.data(Qt.ItemDataRole.UserRole)
        p = self._find_plugin(name)
        if not p:
            return
        text = f"<b>{p.name}</b><br>{p.description or '(no description)'}<br><br>" \
               f"<small>{p.path}</small>"
        if p.error:
            text += f"<br><br><pre style='color:#f48771'>{p.error}</pre>"
        QMessageBox.information(self, "Plugin", text)

    def _open_folder(self) -> None:
        try:
            if sys.platform.startswith("linux"):
                subprocess.Popen(["xdg-open", PLUGIN_DIR])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", PLUGIN_DIR])
            elif sys.platform.startswith("win"):
                os.startfile(PLUGIN_DIR)  # type: ignore[attr-defined]
        except Exception as e:
            QMessageBox.warning(self, "Open folder", f"Could not open: {e}")

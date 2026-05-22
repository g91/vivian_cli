"""File tree sidebar."""
from __future__ import annotations
import os
from PyQt6.QtCore import QDir, Qt, pyqtSignal
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import QHeaderView, QTreeView, QVBoxLayout, QWidget, QLabel


class FileExplorer(QWidget):
    file_opened = pyqtSignal(str)
    root_changed = pyqtSignal(str)

    def __init__(self, root: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header_label = QLabel("EXPLORER")
        self.header_label.setObjectName("explorerHeader")
        layout.addWidget(self.header_label)

        self.model = QFileSystemModel()
        self.model.setRootPath("")
        self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot | QDir.Filter.Hidden)

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setHeaderHidden(True)
        # Hide size/type/date columns
        for col in (1, 2, 3):
            self.tree.setColumnHidden(col, True)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.doubleClicked.connect(self._on_double_clicked)
        layout.addWidget(self.tree)

        self.set_root(root)

    def set_root(self, path: str) -> None:
        path = os.path.abspath(path)
        idx = self.model.setRootPath(path)
        self.tree.setRootIndex(idx)
        self.header_label.setText(f"EXPLORER — {os.path.basename(path) or path}")
        self.root_changed.emit(path)

    def _on_double_clicked(self, index) -> None:
        path = self.model.filePath(index)
        if os.path.isfile(path):
            self.file_opened.emit(path)

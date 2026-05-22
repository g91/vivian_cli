"""Tabbed editor container."""
from __future__ import annotations
import os
from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QTabWidget

from .editor import CodeEditor


class EditorTabs(QTabWidget):
    cursor_changed = pyqtSignal(int, int, str)  # line, col, language
    tab_count_changed = pyqtSignal(int)
    current_file_changed = pyqtSignal(str)      # path of active editor, or ""
    file_saved = pyqtSignal(str)                # absolute path of saved file

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)
        self.tabCloseRequested.connect(self._close_tab)
        self.currentChanged.connect(self._current_changed)

    def tabInserted(self, index: int) -> None:
        super().tabInserted(index)
        self.tab_count_changed.emit(self.count())

    def tabRemoved(self, index: int) -> None:
        super().tabRemoved(index)
        self.tab_count_changed.emit(self.count())

    def open_file(self, path: str) -> Optional[CodeEditor]:
        path = os.path.abspath(path)
        # Already open?
        for i in range(self.count()):
            ed = self.widget(i)
            if isinstance(ed, CodeEditor) and ed.file_path == path:
                self.setCurrentIndex(i)
                return ed
        try:
            ed = CodeEditor(path)
            ed.load(path)
            ed.cursorPositionChanged.connect(lambda e=ed: self._emit_cursor(e))
            ed.document().modificationChanged.connect(lambda m, e=ed: self._mark_dirty(e, m))
            idx = self.addTab(ed, os.path.basename(path))
            self.setTabToolTip(idx, path)
            self.setCurrentIndex(idx)
            return ed
        except Exception as e:
            QMessageBox.critical(self, "Open failed", f"Could not open {path}:\n{e}")
            return None

    def new_untitled(self) -> CodeEditor:
        ed = CodeEditor("")
        ed.cursorPositionChanged.connect(lambda e=ed: self._emit_cursor(e))
        ed.document().modificationChanged.connect(lambda m, e=ed: self._mark_dirty(e, m))
        idx = self.addTab(ed, "Untitled")
        self.setCurrentIndex(idx)
        return ed

    def save_current(self) -> bool:
        ed = self.currentWidget()
        if not isinstance(ed, CodeEditor):
            return False
        path = ed.file_path
        if not path:
            return self.save_current_as()
        try:
            ed.save(path)
            self.setTabText(self.currentIndex(), os.path.basename(path))
            self.file_saved.emit(path)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))
            return False

    def save_current_as(self) -> bool:
        ed = self.currentWidget()
        if not isinstance(ed, CodeEditor):
            return False
        path, _ = QFileDialog.getSaveFileName(self, "Save As", ed.file_path or os.getcwd())
        if not path:
            return False
        try:
            ed.save(path)
            idx = self.currentIndex()
            self.setTabText(idx, os.path.basename(path))
            self.setTabToolTip(idx, path)
            self.file_saved.emit(path)
            self.current_file_changed.emit(path)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))
            return False

    def _close_tab(self, index: int) -> None:
        ed = self.widget(index)
        if isinstance(ed, CodeEditor) and ed.document().isModified():
            reply = QMessageBox.question(
                self, "Unsaved changes",
                f"Save changes to {os.path.basename(ed.file_path) or 'Untitled'}?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            if reply == QMessageBox.StandardButton.Save:
                self.setCurrentIndex(index)
                if not self.save_current():
                    return
        self.removeTab(index)

    def _emit_cursor(self, ed: CodeEditor) -> None:
        if ed is self.currentWidget():
            line, col = ed.cursor_pos()
            self.cursor_changed.emit(line, col, ed.highlighter._language or "text")

    def _current_changed(self, _index: int) -> None:
        ed = self.currentWidget()
        if isinstance(ed, CodeEditor):
            self._emit_cursor(ed)
            self.current_file_changed.emit(ed.file_path or "")
        else:
            self.current_file_changed.emit("")

    def _mark_dirty(self, ed: CodeEditor, modified: bool) -> None:
        idx = self.indexOf(ed)
        if idx < 0:
            return
        name = os.path.basename(ed.file_path) if ed.file_path else "Untitled"
        self.setTabText(idx, ("● " + name) if modified else name)

"""VS Code-style activity bar — vertical icon strip on the far left."""
from __future__ import annotations
from typing import List, Tuple
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QButtonGroup, QFrame, QToolButton, QVBoxLayout, QWidget


# (icon_glyph, tooltip, page_id)
TOP_ITEMS: List[Tuple[str, str, str]] = [
    ("☰", "Explorer", "explorer"),       # ☰
    ("\U0001F50D", "Search", "search"),       # 🔍
    ("⚡", "Source Control", "scm"),      # ⚡ (placeholder)
    ("▶", "Run and Debug", "run"),       # ▶
    ("⧉", "Extensions", "extensions"),   # ⧉
]
BOTTOM_ITEMS: List[Tuple[str, str, str]] = [
    ("⚙", "Settings", "settings"),       # ⚙
]


class ActivityBar(QFrame):
    page_selected = pyqtSignal(str)
    settings_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("activityBar")
        self.setFixedWidth(48)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(0)

        self._buttons: dict[str, QToolButton] = {}
        for glyph, tip, pid in TOP_ITEMS:
            btn = self._make_btn(glyph, tip, pid)
            self._group.addButton(btn)
            layout.addWidget(btn)
            self._buttons[pid] = btn

        layout.addStretch(1)

        for glyph, tip, pid in BOTTOM_ITEMS:
            btn = self._make_btn(glyph, tip, pid, in_group=False)
            btn.clicked.connect(self._on_bottom_clicked(pid))
            layout.addWidget(btn)
            self._buttons[pid] = btn

        # Default selection
        self._buttons["explorer"].setChecked(True)

    def _make_btn(self, glyph: str, tip: str, pid: str, in_group: bool = True) -> QToolButton:
        btn = QToolButton()
        btn.setText(glyph)
        btn.setToolTip(tip)
        btn.setCheckable(in_group)
        btn.setAutoRaise(True)
        btn.setFixedSize(48, 48)
        f = QFont()
        f.setPointSize(18)
        btn.setFont(f)
        if in_group:
            btn.clicked.connect(lambda checked=False, p=pid: self.page_selected.emit(p))
        return btn

    def _on_bottom_clicked(self, pid: str):
        def _fire(_checked=False) -> None:
            if pid == "settings":
                self.settings_requested.emit()
        return _fire

    def select(self, page_id: str) -> None:
        btn = self._buttons.get(page_id)
        if btn and btn.isCheckable():
            btn.setChecked(True)
            self.page_selected.emit(page_id)

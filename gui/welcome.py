"""Welcome screen shown when no tabs are open — mimics VS Code's getting-started."""
from __future__ import annotations
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget,
)


class _Shortcut(QFrame):
    """One row of: action label · shortcut keys."""

    def __init__(self, label: str, keys: list[str], parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(8)

        text = QLabel(label)
        text.setStyleSheet("color: #cccccc; font-size: 14px;")
        layout.addWidget(text)
        layout.addStretch(1)

        for k in keys:
            chip = QLabel(k)
            chip.setStyleSheet(
                "background-color: #3c3c3c; color: #cccccc;"
                "border-radius: 3px; padding: 2px 8px; font-size: 11px;"
            )
            layout.addWidget(chip)
            if k != keys[-1]:
                plus = QLabel("+")
                plus.setStyleSheet("color: #6e6e6e;")
                layout.addWidget(plus)


class WelcomePage(QWidget):
    open_file_clicked = pyqtSignal()
    open_folder_clicked = pyqtSignal()
    new_file_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("welcomePage")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(60, 60, 60, 60)
        outer.addStretch(1)

        # Big title
        title = QLabel("Vivian")
        tf = QFont()
        tf.setPointSize(48)
        tf.setWeight(QFont.Weight.Light)
        title.setFont(tf)
        title.setStyleSheet("color: #cccccc;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(title)

        subtitle = QLabel("Editing evolved · with AI")
        sf = QFont()
        sf.setPointSize(14)
        subtitle.setFont(sf)
        subtitle.setStyleSheet("color: #858585;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(subtitle)

        outer.addSpacing(40)

        # Two columns: Start · Recent (we only have Start for now)
        cols = QHBoxLayout()
        cols.setSpacing(40)
        cols.addStretch(1)

        start_col = QVBoxLayout()
        start_col.setSpacing(2)
        start_title = QLabel("Start")
        start_title.setStyleSheet("color: #cccccc; font-size: 16px; font-weight: 600;")
        start_col.addWidget(start_title)
        start_col.addSpacing(6)

        for label, slot in (
            ("New File…", self.new_file_clicked.emit),
            ("Open File…", self.open_file_clicked.emit),
            ("Open Folder…", self.open_folder_clicked.emit),
        ):
            link = QPushButton(label)
            link.setFlat(True)
            link.setCursor(Qt.CursorShape.PointingHandCursor)
            link.setStyleSheet(
                "QPushButton { background: transparent; color: #4ec9b0; padding: 2px 0;"
                "border: none; text-align: left; font-size: 14px; }"
                "QPushButton:hover { color: #6effd0; }"
            )
            link.clicked.connect(lambda _c, fn=slot: fn())
            start_col.addWidget(link)

        cols.addLayout(start_col)
        cols.addSpacing(60)

        # Shortcut hints
        hints_col = QVBoxLayout()
        hints_col.setSpacing(0)
        hints_title = QLabel("Keyboard Shortcuts")
        hints_title.setStyleSheet("color: #cccccc; font-size: 16px; font-weight: 600;")
        hints_col.addWidget(hints_title)
        hints_col.addSpacing(6)
        for label, keys in (
            ("Open File", ["Ctrl", "O"]),
            ("Open Folder", ["Ctrl", "K", "Ctrl", "O"]),
            ("Toggle AI Panel", ["Ctrl", "Shift", "A"]),
            ("Toggle Explorer", ["Ctrl", "B"]),
            ("Save", ["Ctrl", "S"]),
            ("Settings", ["Ctrl", ","]),
        ):
            hints_col.addWidget(_Shortcut(label, keys))

        cols.addLayout(hints_col)
        cols.addStretch(1)

        outer.addLayout(cols)
        outer.addStretch(2)

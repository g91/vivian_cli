"""VS Code-ish dark theme as a Qt style sheet."""

DARK_QSS = """
QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
    font-family: "Segoe UI", "SF Pro Text", "Helvetica Neue", sans-serif;
    font-size: 13px;
}
QMenuBar { background-color: #3c3c3c; color: #cccccc; }
QMenuBar::item { padding: 4px 10px; background: transparent; }
QMenuBar::item:selected { background-color: #094771; }
QMenu { background-color: #252526; color: #cccccc; border: 1px solid #3c3c3c; }
QMenu::item { padding: 4px 24px 4px 14px; }
QMenu::item:selected { background-color: #094771; }
QMenu::separator { height: 1px; background: #3c3c3c; margin: 4px 0; }

QSplitter::handle { background-color: #252526; }
QSplitter::handle:hover { background-color: #007acc; }

QStatusBar {
    background-color: #007acc;
    color: #ffffff;
    border: none;
    min-height: 22px;
}
QStatusBar QLabel { color: #ffffff; padding: 0 8px; font-size: 12px; }
QStatusBar::item { border: none; }
QStatusBar QToolButton {
    background: transparent;
    color: #ffffff;
    border: none;
    padding: 1px 8px;
    font-size: 12px;
}
QStatusBar QToolButton:hover { background-color: #1f8ad2; }
QStatusBar QToolButton:disabled { color: #b3d8ee; }
QStatusBar QToolButton::menu-indicator { width: 10px; }
QStatusBar QComboBox {
    background-color: #007acc;
    color: #ffffff;
    border: 1px solid #1f8ad2;
    border-radius: 2px;
    padding: 1px 4px;
    min-height: 18px;
    font-size: 12px;
}
QStatusBar QComboBox:hover { background-color: #1f8ad2; }
QStatusBar QComboBox::drop-down { border: none; width: 14px; }
QComboBox QAbstractItemView {
    background-color: #252526;
    color: #cccccc;
    selection-background-color: #094771;
    border: 1px solid #3c3c3c;
    outline: 0;
}

/* ── Activity bar (left strip) ──────────────────────────────────────── */
QFrame#activityBar { background-color: #333333; border: none; }
QFrame#activityBar QToolButton {
    background: transparent;
    color: #858585;
    border: none;
    border-left: 2px solid transparent;
    padding: 6px 0 6px 2px;
}
QFrame#activityBar QToolButton:hover { color: #ffffff; }
QFrame#activityBar QToolButton:checked {
    color: #ffffff;
    border-left: 2px solid #ffffff;
}

/* ── Sidebar / Explorer ─────────────────────────────────────────────── */
QTreeView, QListView {
    background-color: #252526;
    color: #cccccc;
    border: none;
    outline: 0;
    show-decoration-selected: 1;
}
QTreeView::item { padding: 2px 0; }
QTreeView::item:hover { background-color: #2a2d2e; }
QTreeView::item:selected { background-color: #094771; color: #ffffff; }
QTreeView::item:selected:!active { background-color: #37373d; color: #cccccc; }
QHeaderView::section { background-color: #252526; color: #cccccc; border: none; padding: 4px; }

QLabel#explorerHeader, QLabel#aiHeader {
    background-color: #252526;
    color: #bbbbbb;
    padding: 6px 12px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
}

/* ── Tabs ───────────────────────────────────────────────────────────── */
QTabWidget::pane { border: none; background-color: #1e1e1e; }
QTabBar { background-color: #2d2d2d; }
QTabBar::tab {
    background-color: #2d2d2d;
    color: #969696;
    padding: 6px 14px;
    border: none;
    border-right: 1px solid #252526;
    min-width: 80px;
    max-width: 220px;
    height: 26px;
}
QTabBar::tab:selected {
    background-color: #1e1e1e;
    color: #ffffff;
    border-top: 1px solid #007acc;
}
QTabBar::tab:hover:!selected { background-color: #353535; color: #cccccc; }
QTabBar::close-button {
    subcontrol-position: right;
    margin: 2px;
    padding: 0;
    border-radius: 3px;
}
QTabBar::close-button:hover { background-color: #555; }

/* ── Editor ─────────────────────────────────────────────────────────── */
QPlainTextEdit, QTextEdit {
    background-color: #1e1e1e;
    color: #d4d4d4;
    border: none;
    selection-background-color: #264f78;
    font-family: "Cascadia Code", "JetBrains Mono", "Fira Code", "Consolas", "Menlo", monospace;
    font-size: 13px;
}

/* ── Inputs / buttons ───────────────────────────────────────────────── */
QLineEdit {
    background-color: #3c3c3c;
    color: #cccccc;
    border: 1px solid #3c3c3c;
    border-radius: 2px;
    padding: 4px 6px;
}
QLineEdit:focus { border: 1px solid #007acc; }

QPushButton {
    background-color: #0e639c;
    color: #ffffff;
    border: none;
    padding: 5px 14px;
    border-radius: 2px;
}
QPushButton:hover { background-color: #1177bb; }
QPushButton:pressed { background-color: #0d5a8c; }
QPushButton:disabled { background-color: #3c3c3c; color: #888; }

/* ── Welcome page ───────────────────────────────────────────────────── */
QWidget#welcomePage { background-color: #1e1e1e; }

/* ── Scrollbars ─────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background-color: #1e1e1e;
    width: 12px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #424242;
    min-height: 30px;
    border-radius: 3px;
}
QScrollBar::handle:vertical:hover { background-color: #4f4f4f; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background-color: #1e1e1e;
    height: 12px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background-color: #424242;
    min-width: 30px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal:hover { background-color: #4f4f4f; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Tooltips ───────────────────────────────────────────────────────── */
QToolTip {
    background-color: #252526;
    color: #cccccc;
    border: 1px solid #454545;
    padding: 4px 8px;
}
"""

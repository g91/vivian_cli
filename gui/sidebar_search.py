"""Find-in-files panel — ripgrep when available, Python fallback otherwise."""
from __future__ import annotations
import os
import re
import shutil
import subprocess
from typing import Iterable, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)


_BINARY_HINTS = (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".tar",
                 ".gz", ".xz", ".7z", ".so", ".dll", ".exe", ".bin",
                 ".dat", ".db", ".sqlite", ".pyc", ".o", ".a")


def _looks_binary(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in _BINARY_HINTS


def _iter_files(root: str, include: str, exclude: str) -> Iterable[str]:
    include_re = re.compile(include) if include else None
    exclude_re = re.compile(exclude) if exclude else None
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune obvious noise
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", ".venv", "node_modules", "__pycache__", ".idea", ".vscode")]
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            if _looks_binary(full):
                continue
            if include_re and not include_re.search(rel):
                continue
            if exclude_re and exclude_re.search(rel):
                continue
            yield full


def _search_python(query: str, root: str, *, case: bool, whole_word: bool, regex: bool,
                   include: str, exclude: str, limit: int = 2000) -> list[tuple[str, int, str]]:
    if regex:
        pattern = query
    else:
        pattern = re.escape(query)
    if whole_word:
        pattern = rf"\b(?:{pattern})\b"
    flags = 0 if case else re.IGNORECASE
    rx = re.compile(pattern, flags)

    hits: list[tuple[str, int, str]] = []
    for path in _iter_files(root, include, exclude):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, 1):
                    if rx.search(line):
                        hits.append((path, i, line.rstrip("\n")[:400]))
                        if len(hits) >= limit:
                            return hits
        except OSError:
            continue
    return hits


def _search_ripgrep(query: str, root: str, *, case: bool, whole_word: bool, regex: bool,
                    include: str, exclude: str, limit: int = 2000) -> list[tuple[str, int, str]]:
    cmd = ["rg", "--no-heading", "--line-number", "--color=never", "--max-count", "200"]
    if not case:
        cmd.append("-i")
    if whole_word:
        cmd.append("-w")
    if not regex:
        cmd.append("-F")
    if include:
        cmd += ["-g", include]
    if exclude:
        cmd += ["-g", "!" + exclude]
    cmd += ["-e", query, root]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return []
    hits: list[tuple[str, int, str]] = []
    for line in (proc.stdout or "").splitlines():
        # path:lineno:content
        try:
            path, lineno, content = line.split(":", 2)
            hits.append((path, int(lineno), content[:400]))
        except ValueError:
            continue
        if len(hits) >= limit:
            break
    return hits


class SearchPanel(QWidget):
    """Find-in-files. Emits open_at(path, line) when a result is clicked."""
    open_at = pyqtSignal(str, int)

    def __init__(self, root: str, parent=None):
        super().__init__(parent)
        self._root = root
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("SEARCH")
        header.setObjectName("explorerHeader")
        layout.addWidget(header)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(10, 8, 10, 8)
        bl.setSpacing(6)

        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText("Search across workspace…")
        self.query_edit.returnPressed.connect(self._do_search)
        bl.addWidget(self.query_edit)

        opts = QHBoxLayout()
        opts.setSpacing(8)
        self.case_box = QCheckBox("Aa")
        self.case_box.setToolTip("Match case")
        self.word_box = QCheckBox("ab")
        self.word_box.setToolTip("Whole word")
        self.regex_box = QCheckBox(".*")
        self.regex_box.setToolTip("Regular expression")
        for cb in (self.case_box, self.word_box, self.regex_box):
            opts.addWidget(cb)
        opts.addStretch(1)
        bl.addLayout(opts)

        self.include_edit = QLineEdit()
        self.include_edit.setPlaceholderText("Files to include (glob/regex)")
        bl.addWidget(self.include_edit)

        self.exclude_edit = QLineEdit()
        self.exclude_edit.setPlaceholderText("Files to exclude (glob/regex)")
        bl.addWidget(self.exclude_edit)

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self._do_search)
        bl.addWidget(self.search_btn)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #858585; font-size: 11px;")
        bl.addWidget(self.status_label)

        layout.addWidget(body)

        self.results = QTreeWidget()
        self.results.setHeaderHidden(True)
        self.results.setRootIsDecorated(True)
        self.results.itemActivated.connect(self._on_result_clicked)
        self.results.itemClicked.connect(self._on_result_clicked)
        layout.addWidget(self.results, 1)

    def set_root(self, root: str) -> None:
        self._root = root

    def focus_query(self) -> None:
        self.query_edit.setFocus()
        self.query_edit.selectAll()

    def _do_search(self) -> None:
        query = self.query_edit.text().strip()
        if not query:
            self.results.clear()
            self.status_label.setText("")
            return
        case = self.case_box.isChecked()
        word = self.word_box.isChecked()
        regex = self.regex_box.isChecked()
        include = self.include_edit.text().strip()
        exclude = self.exclude_edit.text().strip()

        engine = "ripgrep" if shutil.which("rg") else "python"
        runner = _search_ripgrep if engine == "ripgrep" else _search_python
        hits = runner(query, self._root, case=case, whole_word=word, regex=regex,
                      include=include, exclude=exclude)

        self.results.clear()
        by_file: dict[str, list[tuple[int, str]]] = {}
        for path, lineno, content in hits:
            by_file.setdefault(path, []).append((lineno, content))

        for path in sorted(by_file):
            rel = os.path.relpath(path, self._root)
            file_item = QTreeWidgetItem([f"{rel}  ({len(by_file[path])})"])
            file_item.setData(0, Qt.ItemDataRole.UserRole, ("file", path, 0))
            for lineno, content in by_file[path]:
                child = QTreeWidgetItem([f"{lineno}: {content}"])
                child.setData(0, Qt.ItemDataRole.UserRole, ("hit", path, lineno))
                file_item.addChild(child)
            self.results.addTopLevelItem(file_item)
            file_item.setExpanded(True)

        total = sum(len(v) for v in by_file.values())
        self.status_label.setText(f"{total} match{'es' if total != 1 else ''} in {len(by_file)} file{'s' if len(by_file) != 1 else ''}  ·  {engine}")

    def _on_result_clicked(self, item: QTreeWidgetItem, _col: int = 0) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        kind, path, lineno = data
        if kind == "hit":
            self.open_at.emit(path, int(lineno))
        elif kind == "file":
            self.open_at.emit(path, 1)

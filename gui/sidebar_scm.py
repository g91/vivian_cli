"""Source-control panel — git status, stage, commit, pull/push/fetch/merge."""
from __future__ import annotations
import os
import subprocess
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)


def _run_git(root: str, *args: str, timeout: int = 8) -> tuple[int, str, str]:
    try:
        p = subprocess.run(["git", "-C", root, *args],
                           capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout or "", p.stderr or ""
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", str(e)


def _is_repo(root: str) -> bool:
    rc, _, _ = _run_git(root, "rev-parse", "--is-inside-work-tree", timeout=3)
    return rc == 0


class SCMPanel(QWidget):
    """Git UI. Long-running ops are dispatched via the run_git_command signal so
    the MainWindow can stream them through the shared output dock."""

    run_git_command = pyqtSignal(list, str)  # args, description
    open_file = pyqtSignal(str)              # absolute path

    def __init__(self, root: str, parent=None):
        super().__init__(parent)
        self._root = root
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("SOURCE CONTROL")
        header.setObjectName("explorerHeader")
        layout.addWidget(header)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(10, 8, 10, 8)
        bl.setSpacing(6)

        self.branch_label = QLabel("")
        self.branch_label.setStyleSheet("color: #cccccc;")
        bl.addWidget(self.branch_label)

        action_row = QHBoxLayout()
        action_row.setSpacing(4)
        for label, slot in (
            ("Pull",   self._pull),
            ("Push",   self._push),
            ("Fetch",  self._fetch),
            ("Merge…", self._merge),
            ("⟳",      self.refresh),
        ):
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(slot)
            action_row.addWidget(btn)
        bl.addLayout(action_row)

        self.commit_msg = QPlainTextEdit()
        self.commit_msg.setPlaceholderText("Commit message (Ctrl+Enter to commit)")
        self.commit_msg.setFixedHeight(64)
        f = QFont()
        f.setPointSize(11)
        self.commit_msg.setFont(f)
        bl.addWidget(self.commit_msg)

        commit_row = QHBoxLayout()
        commit_row.setSpacing(4)
        self.commit_btn = QPushButton("Commit")
        self.commit_btn.clicked.connect(lambda: self._commit(push=False))
        commit_row.addWidget(self.commit_btn)
        self.commit_push_btn = QPushButton("Commit & Push")
        self.commit_push_btn.clicked.connect(lambda: self._commit(push=True))
        commit_row.addWidget(self.commit_push_btn)
        commit_row.addStretch(1)
        bl.addLayout(commit_row)

        layout.addWidget(body)

        # Staged
        staged_header = QLabel("STAGED CHANGES")
        staged_header.setStyleSheet(
            "color: #bbbbbb; background-color: #252526;"
            "padding: 4px 10px; font-size: 11px; font-weight: 600;"
        )
        layout.addWidget(staged_header)
        self.staged_list = QListWidget()
        self.staged_list.itemActivated.connect(self._unstage_item)
        layout.addWidget(self.staged_list)

        changes_header = QLabel("CHANGES")
        changes_header.setStyleSheet(
            "color: #bbbbbb; background-color: #252526;"
            "padding: 4px 10px; font-size: 11px; font-weight: 600;"
        )
        layout.addWidget(changes_header)
        self.changes_list = QListWidget()
        self.changes_list.itemActivated.connect(self._stage_item)
        layout.addWidget(self.changes_list)

        self._staged_header_w = staged_header
        self._changes_header_w = changes_header

        self.refresh()

    # ── public ────────────────────────────────────────────────────────────
    def set_root(self, root: str) -> None:
        self._root = root
        self.refresh()

    def refresh(self) -> None:
        if not _is_repo(self._root):
            self.branch_label.setText("(not a git repository)")
            self.staged_list.clear()
            self.changes_list.clear()
            self._staged_header_w.setText("STAGED CHANGES")
            self._changes_header_w.setText("CHANGES")
            return

        # Branch + ahead/behind
        _, branch, _ = _run_git(self._root, "branch", "--show-current")
        branch = branch.strip()
        _, ahead_behind, _ = _run_git(
            self._root, "rev-list", "--left-right", "--count",
            f"{branch}...@{{upstream}}", timeout=4,
        )
        suffix = ""
        parts = ahead_behind.strip().split()
        if len(parts) == 2:
            ahead, behind = parts
            if ahead != "0" or behind != "0":
                suffix = f"   ↑{ahead}  ↓{behind}"
        self.branch_label.setText(f"⎇  {branch or '(detached)'}{suffix}")

        # Status
        _, status, _ = _run_git(self._root, "status", "--porcelain=v1")
        self.staged_list.clear()
        self.changes_list.clear()
        for line in status.splitlines():
            if len(line) < 3:
                continue
            x, y, path = line[0], line[1], line[3:]
            label = f"{x}{y}  {path}"
            if x != " " and x != "?":
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, path)
                self.staged_list.addItem(item)
            if y != " " or x == "?":
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, path)
                self.changes_list.addItem(item)

        self._staged_header_w.setText(f"STAGED CHANGES   ({self.staged_list.count()})")
        self._changes_header_w.setText(f"CHANGES   ({self.changes_list.count()})")

    # ── slots ─────────────────────────────────────────────────────────────
    def _stage_item(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path:
            return
        rc, _, err = _run_git(self._root, "add", "--", path)
        if rc != 0:
            QMessageBox.warning(self, "git add failed", err.strip() or "Unknown error")
        self.refresh()

    def _unstage_item(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path:
            return
        rc, _, err = _run_git(self._root, "reset", "HEAD", "--", path)
        if rc != 0:
            QMessageBox.warning(self, "git reset failed", err.strip() or "Unknown error")
        self.refresh()

    def _commit(self, push: bool) -> None:
        msg = self.commit_msg.toPlainText().strip()
        if not msg:
            QMessageBox.information(self, "Commit", "Enter a commit message first.")
            return
        if self.staged_list.count() == 0:
            QMessageBox.information(self, "Commit", "No staged changes. Double-click files in CHANGES to stage them.")
            return
        rc, out, err = _run_git(self._root, "commit", "-m", msg, timeout=15)
        if rc != 0:
            QMessageBox.warning(self, "git commit failed", (err or out).strip() or "Unknown error")
            return
        self.commit_msg.clear()
        self.refresh()
        if push:
            self._push()

    def _pull(self) -> None:
        self.run_git_command.emit(["pull", "--ff-only"], "git pull --ff-only")

    def _push(self) -> None:
        self.run_git_command.emit(["push"], "git push")

    def _fetch(self) -> None:
        self.run_git_command.emit(["fetch", "--all", "--prune"], "git fetch --all --prune")

    def _merge(self) -> None:
        branch, ok = QInputDialog.getText(self, "Merge", "Branch to merge into current:")
        if not ok or not branch.strip():
            return
        self.run_git_command.emit(["merge", "--no-edit", branch.strip()], f"git merge {branch.strip()}")

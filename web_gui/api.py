"""Stateless REST helpers used by the web GUI's HTTP handlers."""
from __future__ import annotations
import os
import re
import shlex
import shutil
import subprocess
from typing import Any

from ..gui.build_detect import (compiler_for_file, detect_project,
                                is_esp_idf_project, ProjectKind)


_BINARY_HINTS = (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".tar",
                 ".gz", ".xz", ".7z", ".so", ".dll", ".exe", ".bin",
                 ".dat", ".db", ".sqlite", ".pyc", ".o", ".a")
_HIDDEN_DIRS = (".git", ".venv", "node_modules", "__pycache__", ".idea", ".vscode")


# ── filesystem ─────────────────────────────────────────────────────────
def list_tree(path: str) -> dict:
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        return {"error": "not a directory", "path": path}
    entries = []
    try:
        for name in sorted(os.listdir(path), key=lambda s: (not os.path.isdir(os.path.join(path, s)), s.lower())):
            full = os.path.join(path, name)
            entries.append({
                "name": name,
                "path": full,
                "is_dir": os.path.isdir(full),
                "hidden": name.startswith("."),
            })
    except OSError as e:
        return {"error": str(e), "path": path}
    return {"path": path, "entries": entries}


def read_file(path: str) -> dict:
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        return {"error": "not a file", "path": path}
    if os.path.splitext(path)[1].lower() in _BINARY_HINTS:
        return {"error": "binary file not supported", "path": path}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError as e:
        return {"error": str(e), "path": path}
    return {"path": path, "content": content}


def write_file(path: str, content: str) -> dict:
    path = os.path.abspath(path)
    parent = os.path.dirname(path)
    if not os.path.isdir(parent):
        return {"error": "parent directory does not exist", "path": path}
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        return {"error": str(e), "path": path}
    return {"ok": True, "path": path, "bytes": len(content.encode("utf-8"))}


# ── search ─────────────────────────────────────────────────────────────
def _iter_files(root: str, include: str, exclude: str):
    include_re = re.compile(include) if include else None
    exclude_re = re.compile(exclude) if exclude else None
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _HIDDEN_DIRS]
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            if os.path.splitext(full)[1].lower() in _BINARY_HINTS:
                continue
            if include_re and not include_re.search(rel):
                continue
            if exclude_re and exclude_re.search(rel):
                continue
            yield full


def search(root: str, *, query: str, case: bool, word: bool, regex: bool,
           include: str, exclude: str, limit: int = 2000) -> dict:
    if not query:
        return {"hits": [], "engine": "noop", "total": 0}

    # ripgrep is faster — use it when available
    if shutil.which("rg"):
        cmd = ["rg", "--no-heading", "--line-number", "--color=never", "--max-count", "200"]
        if not case:
            cmd.append("-i")
        if word:
            cmd.append("-w")
        if not regex:
            cmd.append("-F")
        if include:
            cmd += ["-g", include]
        if exclude:
            cmd += ["-g", "!" + exclude]
        cmd += ["-e", query, root]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as e:
            return {"error": str(e)}
        hits = []
        for line in (r.stdout or "").splitlines():
            try:
                p, ln, content = line.split(":", 2)
                hits.append({"path": p, "line": int(ln), "text": content[:400]})
            except ValueError:
                continue
            if len(hits) >= limit:
                break
        return {"hits": hits, "engine": "ripgrep", "total": len(hits)}

    # Python fallback
    pattern = query if regex else re.escape(query)
    if word:
        pattern = rf"\b(?:{pattern})\b"
    flags = 0 if case else re.IGNORECASE
    rx = re.compile(pattern, flags)
    hits = []
    for path in _iter_files(root, include, exclude):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, 1):
                    if rx.search(line):
                        hits.append({"path": path, "line": i, "text": line.rstrip("\n")[:400]})
                        if len(hits) >= limit:
                            return {"hits": hits, "engine": "python", "total": len(hits)}
        except OSError:
            continue
    return {"hits": hits, "engine": "python", "total": len(hits)}


# ── git ────────────────────────────────────────────────────────────────
def _git(root: str, *args: str, timeout: int = 8) -> tuple[int, str, str]:
    try:
        p = subprocess.run(["git", "-C", root, *args],
                           capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout or "", p.stderr or ""
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", str(e)


def git_status(root: str) -> dict:
    rc, _, _ = _git(root, "rev-parse", "--is-inside-work-tree", timeout=3)
    if rc != 0:
        return {"is_repo": False}
    _, branch, _ = _git(root, "branch", "--show-current")
    branch = branch.strip()
    ahead, behind = 0, 0
    _, ab, _ = _git(root, "rev-list", "--left-right", "--count",
                    f"{branch}...@{{upstream}}", timeout=4)
    parts = ab.strip().split()
    if len(parts) == 2:
        try:
            ahead, behind = int(parts[0]), int(parts[1])
        except ValueError:
            pass
    staged, changes = [], []
    _, status, _ = _git(root, "status", "--porcelain=v1")
    for line in status.splitlines():
        if len(line) < 3:
            continue
        x, y, path = line[0], line[1], line[3:]
        entry = {"x": x, "y": y, "path": path}
        if x not in (" ", "?"):
            staged.append(entry)
        if y != " " or x == "?":
            changes.append(entry)
    return {
        "is_repo": True, "branch": branch,
        "ahead": ahead, "behind": behind,
        "staged": staged, "changes": changes,
    }


def git_action(root: str, body: dict) -> dict:
    action = body.get("action", "")
    if action == "stage":
        rc, _, err = _git(root, "add", "--", body.get("path", ""))
        return {"ok": rc == 0, "error": err.strip()}
    if action == "unstage":
        rc, _, err = _git(root, "reset", "HEAD", "--", body.get("path", ""))
        return {"ok": rc == 0, "error": err.strip()}
    if action == "commit":
        msg = body.get("message", "").strip()
        if not msg:
            return {"ok": False, "error": "empty message"}
        rc, out, err = _git(root, "commit", "-m", msg, timeout=15)
        return {"ok": rc == 0, "error": (err or out).strip()}
    return {"ok": False, "error": f"unknown action: {action}"}


# ── build / run dispatch ───────────────────────────────────────────────
def build_info(root: str, current_file: str) -> dict:
    """Tell the frontend what controls to show and what command Build will run."""
    info: dict[str, Any] = {
        "is_esp": is_esp_idf_project(root),
        "compiler": None,
        "kind": "unknown",
    }
    if info["is_esp"]:
        info["kind"] = "esp-idf"
        return info
    try:
        entries = set(os.listdir(root))
    except OSError:
        entries = set()
    if any(n in entries for n in ("Makefile", "makefile", "GNUmakefile")):
        info["kind"] = "make"
        info["compiler"] = "make"
        return info
    recipe = compiler_for_file(current_file) if current_file else None
    if recipe:
        info["kind"] = "single-file"
        info["compiler"] = recipe["label"]
    return info


def resolve_run_argv(*, kind: str, target: str, method: str,
                     file: str, argv_raw: str, cwd: str) -> list | dict:
    """Build the actual subprocess argv for the streaming endpoint.

    On failure returns ``{"error": "..."}`` so the caller can 400 it.
    """
    if kind == "build":
        if is_esp_idf_project(cwd):
            t = target or "esp32"
            return ["idf.py", f"-DIDF_TARGET={t}", "build"]
        try:
            entries = set(os.listdir(cwd))
        except OSError:
            entries = set()
        if any(n in entries for n in ("Makefile", "makefile", "GNUmakefile")):
            return ["make"]
        recipe = compiler_for_file(file) if file else None
        if recipe:
            return recipe["argv"]
        return {"error": "no buildable target detected"}

    if kind == "flash":
        if not is_esp_idf_project(cwd):
            return {"error": "flash is only wired for ESP-IDF projects"}
        t = target or "esp32"
        if method == "jtag":
            return ["idf.py", f"-DIDF_TARGET={t}", "openocd", "flash"]
        if method == "dfu":
            return ["idf.py", f"-DIDF_TARGET={t}", "dfu-flash"]
        return ["idf.py", f"-DIDF_TARGET={t}", "flash"]

    if kind == "run":
        if not argv_raw:
            return {"error": "missing argv"}
        try:
            return shlex.split(argv_raw)
        except ValueError as e:
            return {"error": f"argv parse: {e}"}

    if kind == "git":
        if not argv_raw:
            return {"error": "missing git args"}
        try:
            args = shlex.split(argv_raw)
        except ValueError as e:
            return {"error": f"argv parse: {e}"}
        return ["git", "-C", cwd, *args]

    return {"error": f"unknown kind: {kind}"}

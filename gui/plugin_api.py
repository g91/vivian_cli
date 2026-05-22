"""Vivian IDE plugin API + loader.

A plugin is a single .py file in ``~/.vivian/plugins/``. Each plugin defines a
top-level function:

    def register(api):
        api.add_menu_action("Tools", "Say hi", lambda: api.show_message("Hi"))
        api.on_file_opened(lambda path: print("opened:", path))

The IDE calls ``register(api)`` once at load time. Plugins can be enabled or
disabled at runtime; disabling a plugin re-imports the module and re-runs
``register`` next time it's enabled, so state is rebuilt cleanly.
"""
from __future__ import annotations
import importlib.util
import json
import os
import sys
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMessageBox


PLUGIN_DIR = os.path.expanduser("~/.vivian/plugins")
STATE_FILE = os.path.expanduser("~/.vivian/plugins.json")


@dataclass
class PluginInfo:
    name: str
    path: str
    description: str = ""
    enabled: bool = False
    module: Optional[Any] = None
    actions: list[QAction] = field(default_factory=list)
    error: str = ""


class PluginAPI:
    """Surface exposed to plugins. Methods here are stable; add new ones rather
    than changing signatures."""

    def __init__(self, window):
        self._window = window
        self._file_open_listeners: list[Callable[[str], None]] = []
        self._save_listeners: list[Callable[[str], None]] = []
        self._registered_actions: list[QAction] = []

    # ── public to plugins ────────────────────────────────────────────────
    def add_menu_action(self, menu_name: str, label: str,
                        callback: Callable[[], None]) -> QAction:
        menubar = self._window.menuBar()
        target = None
        for action in menubar.actions():
            if action.menu() and action.menu().title().replace("&", "") == menu_name:
                target = action.menu()
                break
        if target is None:
            target = menubar.addMenu(menu_name)
        act = QAction(label, self._window)
        act.triggered.connect(lambda checked=False: callback())
        target.addAction(act)
        self._registered_actions.append(act)
        return act

    def show_message(self, text: str, title: str = "Vivian IDE") -> None:
        QMessageBox.information(self._window, title, text)

    def current_file(self) -> str:
        return self._window._current_file()

    def current_workspace(self) -> str:
        return self._window.runner.project_root

    def open_file(self, path: str) -> None:
        self._window.tabs.open_file(path)

    def on_file_opened(self, cb: Callable[[str], None]) -> None:
        self._file_open_listeners.append(cb)

    def on_file_saved(self, cb: Callable[[str], None]) -> None:
        self._save_listeners.append(cb)

    # ── public to IDE ────────────────────────────────────────────────────
    def fire_file_opened(self, path: str) -> None:
        for cb in list(self._file_open_listeners):
            try:
                cb(path)
            except Exception as e:
                print(f"[plugin] file_opened handler failed: {e}", file=sys.stderr)

    def fire_file_saved(self, path: str) -> None:
        for cb in list(self._save_listeners):
            try:
                cb(path)
            except Exception as e:
                print(f"[plugin] file_saved handler failed: {e}", file=sys.stderr)

    def detach(self, info: "PluginInfo") -> None:
        """Remove menu actions added on behalf of a plugin and forget its
        listeners. Called when a plugin is disabled."""
        for act in info.actions:
            act.setVisible(False)
            parent = act.parent()
            try:
                act.deleteLater()
            except Exception:
                pass
        info.actions.clear()

    def claim_pending_actions(self, info: "PluginInfo") -> None:
        """Assign every action queued during a register() call to the plugin."""
        info.actions.extend(self._registered_actions)
        self._registered_actions.clear()


# ── loader ───────────────────────────────────────────────────────────────
def discover_plugins() -> list[PluginInfo]:
    os.makedirs(PLUGIN_DIR, exist_ok=True)
    enabled_state = _load_state()
    plugins: list[PluginInfo] = []
    for fname in sorted(os.listdir(PLUGIN_DIR)):
        if not fname.endswith(".py") or fname.startswith("_"):
            continue
        path = os.path.join(PLUGIN_DIR, fname)
        name = os.path.splitext(fname)[0]
        desc = _extract_description(path)
        plugins.append(PluginInfo(
            name=name, path=path, description=desc,
            enabled=enabled_state.get(name, False),
        ))
    return plugins


def load_plugin(info: PluginInfo, api: PluginAPI) -> None:
    """Import the module and call register(api). Mutates ``info``."""
    spec = importlib.util.spec_from_file_location(f"vivian_plugin_{info.name}", info.path)
    if spec is None or spec.loader is None:
        info.error = "spec_from_file_location failed"
        return
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        info.error = traceback.format_exc()
        return
    register_fn = getattr(module, "register", None)
    if not callable(register_fn):
        info.error = "missing register(api) function"
        return
    try:
        register_fn(api)
    except Exception:
        info.error = traceback.format_exc()
        return
    api.claim_pending_actions(info)
    info.module = module
    info.error = ""


def unload_plugin(info: PluginInfo, api: PluginAPI) -> None:
    api.detach(info)
    info.module = None


def save_state(plugins: list[PluginInfo]) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    data = {p.name: p.enabled for p in plugins}
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _load_state() -> dict[str, bool]:
    if not os.path.isfile(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _extract_description(path: str) -> str:
    """First non-empty line of the module docstring or top-line comment."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(2000)
    except OSError:
        return ""
    head = head.lstrip()
    if head.startswith('"""') or head.startswith("'''"):
        quote = head[:3]
        end = head.find(quote, 3)
        if end > 3:
            body = head[3:end].strip().splitlines()
            for line in body:
                if line.strip():
                    return line.strip()[:140]
    for line in head.splitlines():
        s = line.strip()
        if s.startswith("#") and len(s) > 1:
            return s.lstrip("# ").strip()[:140]
        if s and not s.startswith("from") and not s.startswith("import"):
            break
    return ""


# ── starter plugin so the user has something to crib from ──────────────
EXAMPLE_PLUGIN = '''"""Hello — example plugin. Adds a Tools → Say Hi action.

Plugins are plain Python files in ~/.vivian/plugins/. The IDE imports the file
and calls register(api). The `api` object lets you add menu items, observe
file events, and prompt the user.
"""


def register(api):
    api.add_menu_action("Tools", "Say hi", lambda: api.show_message("Hello from a plugin!"))
    api.on_file_opened(lambda path: print(f"[hello] opened: {path}"))
'''


def ensure_example_plugin() -> None:
    """Write the example plugin on first run so the folder isn't empty."""
    os.makedirs(PLUGIN_DIR, exist_ok=True)
    example = os.path.join(PLUGIN_DIR, "hello.py")
    if not os.path.exists(example):
        with open(example, "w", encoding="utf-8") as f:
            f.write(EXAMPLE_PLUGIN)

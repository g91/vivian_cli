"""Utilities module."""
from .context import build_system_prompt, get_git_status, get_vivian_md_content
from .format import format_duration, format_number, format_cost, format_bytes, truncate
from .history import HistoryManager

__all__ = [
    "build_system_prompt",
    "get_git_status",
    "get_vivian_md_content",
    "format_duration",
    "format_number",
    "format_cost",
    "format_bytes",
    "truncate",
    "HistoryManager",
    "KeybindingManager",
    "DEFAULT_BINDINGS",
]


def __getattr__(name: str):
    if name in {"KeybindingManager", "DEFAULT_BINDINGS"}:
        from .keybindings import DEFAULT_BINDINGS, KeybindingManager

        exports = {
            "KeybindingManager": KeybindingManager,
            "DEFAULT_BINDINGS": DEFAULT_BINDINGS,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

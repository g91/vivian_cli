"""Port of src/utils/hooks/__init__ (source not found)"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parent.parent / "hooks.py"
_SPEC = importlib.util.spec_from_file_location("vivian_cli.utils._hooks_runtime", _MODULE_PATH)
if _SPEC is None or _SPEC.loader is None:
	raise ImportError(f"Unable to load hooks runtime from {_MODULE_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

execute_notification_hooks = _MODULE.execute_notification_hooks
execute_file_changed_hooks = _MODULE.execute_file_changed_hooks
hooks = _MODULE.hooks

__all__ = ["execute_notification_hooks", "execute_file_changed_hooks", "hooks"]

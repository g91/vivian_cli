"""Port of src/utils/computerUse/inputLoader.ts."""
from __future__ import annotations

import importlib
import os


_cached = None


def requireComputerUseInput():
    global _cached
    if _cached is not None:
        return _cached
    module_name = os.environ.get("COMPUTER_USE_INPUT_NODE_PATH") or "computer_use_input"
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise RuntimeError(f"Failed to load computer-use input module: {module_name}") from exc
    if getattr(module, "isSupported", True) is False:
        raise RuntimeError("@ant/computer-use-input is not supported on this platform")
    _cached = module
    return _cached


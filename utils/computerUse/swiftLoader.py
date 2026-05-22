"""Port of src/utils/computerUse/swiftLoader.ts."""
from __future__ import annotations

import importlib
import os
import sys


_cached = None


def requireComputerUseSwift():
    global _cached
    if sys.platform != "darwin":
        raise RuntimeError("@ant/computer-use-swift is macOS-only")
    if _cached is not None:
        return _cached
    module_name = os.environ.get("COMPUTER_USE_SWIFT_NODE_PATH") or "computer_use_swift"
    try:
        _cached = importlib.import_module(module_name)
    except Exception as exc:
        raise RuntimeError(f"Failed to load computer-use swift module: {module_name}") from exc
    return _cached


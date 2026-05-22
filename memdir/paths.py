"""Memory directory path resolution — mirrors src/memdir/paths.ts."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

_AUTO_MEM_DIRNAME = "memory"
_AUTO_MEM_ENTRYPOINT_NAME = "MEMORY.md"


def _is_env_truthy(val: Optional[str]) -> bool:
    return val is not None and val.lower() not in ("", "0", "false", "no")


def _is_env_defined_falsy(val: Optional[str]) -> bool:
    return val is not None and val.lower() in ("0", "false", "no")


def is_auto_memory_enabled() -> bool:
    """Check env/settings to decide if auto-memory features are on."""
    env_val = os.environ.get("vivian_CODE_DISABLE_AUTO_MEMORY")
    if _is_env_truthy(env_val):
        return False
    if _is_env_defined_falsy(env_val):
        return True
    if _is_env_truthy(os.environ.get("vivian_CODE_SIMPLE")):
        return False
    if _is_env_truthy(os.environ.get("vivian_CODE_REMOTE")) and not os.environ.get(
        "vivian_CODE_REMOTE_MEMORY_DIR"
    ):
        return False
    try:
        import json

        settings_path = Path.home() / ".vivian" / "settings.json"
        settings = json.loads(settings_path.read_text())
        if "autoMemoryEnabled" in settings:
            return bool(settings["autoMemoryEnabled"])
    except Exception:
        pass
    return True


def is_extract_mode_active() -> bool:
    return False  # Feature flag — disabled by default in Python port


def get_memory_base_dir() -> str:
    remote_dir = os.environ.get("vivian_CODE_REMOTE_MEMORY_DIR")
    if remote_dir:
        return remote_dir
    return str(Path.home() / ".vivian")


def get_auto_mem_path() -> Optional[str]:
    try:
        import json

        settings_path = Path.home() / ".vivian" / "settings.json"
        settings = json.loads(settings_path.read_text())
        custom = settings.get("autoMemoryPath")
        if custom:
            expanded = str(Path(custom.replace("~/", str(Path.home()) + "/")).resolve())
            if len(expanded) >= 3 and "\x00" not in expanded:
                return expanded.rstrip("/\\") + "/"
    except Exception:
        pass
    return None


def get_memory_dir() -> str:
    custom = get_auto_mem_path()
    if custom:
        return custom
    return str(Path(get_memory_base_dir()) / _AUTO_MEM_DIRNAME)

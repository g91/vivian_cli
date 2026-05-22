"""Shared GUI chat configuration for Qt and web frontends."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..utils.envUtils import get_vivian_config_home_dir
from .chat_modes import available_chat_modes

_CONFIG_FILENAME = "gui-chat-settings.json"


def get_gui_chat_config_path() -> Path:
    return Path(get_vivian_config_home_dir()) / _CONFIG_FILENAME


def _default_user_settings() -> dict[str, Any]:
    return {
        "model": None,
        "permission_mode": None,
        "append_system_prompt": "",
        "include_open_file_by_default": False,
        "show_internal_modes": True,
        "advisor_model": None,
    }


def default_gui_chat_config() -> dict[str, Any]:
    return {
        "is_employee": True,
        "default_mode": "default",
        "enabled_modes": [],
        "user_settings": _default_user_settings(),
        "web_settings": {
            "font_size": 13,
            "editor_minimap": True,
            "word_wrap": False,
        },
        "gui_settings": {
            "include_open_file_by_default": False,
        },
    }


def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(dict(merged[key]), value)
        else:
            merged[key] = value
    return merged


def load_gui_chat_config() -> dict[str, Any]:
    path = get_gui_chat_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    defaults = default_gui_chat_config()
    if not path.exists():
        save_gui_chat_config(defaults)
        return annotate_gui_chat_config(defaults)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    merged = _merge_dict(defaults, raw)
    save_gui_chat_config(merged)
    return annotate_gui_chat_config(merged)


def save_gui_chat_config(config: dict[str, Any]) -> dict[str, Any]:
    path = get_gui_chat_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _merge_dict(default_gui_chat_config(), config if isinstance(config, dict) else {})
    path.write_text(json.dumps(normalized, indent=2, sort_keys=True), encoding="utf-8")
    return annotate_gui_chat_config(normalized)


def annotate_gui_chat_config(config: dict[str, Any]) -> dict[str, Any]:
    annotated = _merge_dict(default_gui_chat_config(), config)
    annotated["is_employee"] = True
    is_employee = True
    user_settings = annotated.get("user_settings") or {}
    user_settings["show_internal_modes"] = True
    annotated["user_settings"] = user_settings
    expose_internal = True
    modes = available_chat_modes(is_employee=is_employee, expose_internal_modes=expose_internal)
    allowed_ids = {item["id"] for item in modes}
    enabled = annotated.get("enabled_modes") or []
    if enabled:
        modes = [item for item in modes if item["id"] in set(enabled)]
        if not modes:
            modes = available_chat_modes(is_employee=is_employee, expose_internal_modes=expose_internal)
    default_mode = annotated.get("default_mode")
    if default_mode not in {item["id"] for item in modes}:
        annotated["default_mode"] = modes[0]["id"] if modes else "default"
    annotated["available_modes"] = modes
    annotated["config_path"] = str(get_gui_chat_config_path())
    annotated["employee_capabilities"] = {
        "is_employee": True,
        "show_internal_modes": True,
        "can_use_internal_modes": True,
    }
    annotated["changeable_settings"] = {
        "top_level": ["is_employee", "default_mode", "enabled_modes"],
        "user_settings": sorted(_default_user_settings().keys()),
        "web_settings": ["font_size", "editor_minimap", "word_wrap"],
        "gui_settings": ["include_open_file_by_default"],
    }
    return annotated


def apply_gui_chat_config(engine: Any, config: dict[str, Any]) -> dict[str, Any]:
    effective = annotate_gui_chat_config(config)
    user_settings = effective.get("user_settings") or {}
    model = user_settings.get("model")
    if model:
        setattr(engine, "model", model)
    permission_mode = user_settings.get("permission_mode")
    if permission_mode:
        setattr(engine, "permission_mode", permission_mode)
    append_system_prompt = user_settings.get("append_system_prompt")
    if isinstance(append_system_prompt, str):
        setattr(engine, "append_system_prompt", append_system_prompt or None)
    setattr(engine, "gui_chat_config", effective)
    return effective

"""Auto-mode subcommand handlers — mirrors src/cli/handlers/autoMode.ts.

Dumps default/merged classifier rules and can critique user-written rules.
Dynamically imported when ``vivian auto-mode ...`` runs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional


def _load_config_value(key: str, default: Any = None) -> Any:
    try:
        cfg_path = Path.home() / ".vivian" / "config.json"
        cfg = json.loads(cfg_path.read_text())
        return cfg.get(key, default)
    except Exception:
        return default


DEFAULT_AUTO_MODE_RULES: dict[str, list[str]] = {
    "allow": [
        "Read files, directories, and git history",
        "Search code with grep/glob",
        "Run tests",
        "Install project dependencies (npm/pip/cargo)",
        "Format code",
    ],
    "soft_deny": [
        "Delete files permanently",
        "Force-push to git",
        "DROP/TRUNCATE database tables",
        "Expose secrets or credentials",
        "Send emails or messages",
    ],
    "environment": [
        "Development machine with internet access",
    ],
}


def get_default_auto_mode_rules() -> dict[str, list[str]]:
    """Return the built-in default auto-mode classifier rules."""
    return dict(DEFAULT_AUTO_MODE_RULES)


def get_auto_mode_config() -> Optional[dict[str, list[str]]]:
    """Return user-configured auto-mode rules from config.json, if any."""
    return _load_config_value("autoModeRules")


def auto_mode_defaults_handler() -> None:
    """Print the default classifier rules as JSON."""
    print(json.dumps(get_default_auto_mode_rules(), indent=2))


def auto_mode_config_handler() -> None:
    """Print the effective auto-mode config (user overrides merged with defaults)."""
    user_cfg = get_auto_mode_config()
    defaults = get_default_auto_mode_rules()
    effective: dict[str, list[str]] = {}
    for section in ("allow", "soft_deny", "environment"):
        user_val = (user_cfg or {}).get(section, [])
        effective[section] = user_val if user_val else defaults[section]
    print(json.dumps(effective, indent=2))


CRITIQUE_SYSTEM_PROMPT = (
    "You are an expert reviewer of auto mode classifier rules for Vivian.\n"
    "\n"
    "Vivian has an 'auto mode' that uses an AI classifier to decide whether "
    "tool calls should be auto-approved or require user confirmation. Users can "
    "write custom rules in three categories:\n"
    "\n"
    "- **allow**: Actions the classifier should auto-approve\n"
    "- **soft_deny**: Actions the classifier should block\n"
    "- **environment**: Context about the user's setup\n"
    "\n"
    "Your job is to critique the user's custom rules for clarity, completeness, "
    "and potential issues.\n"
    "\n"
    "For each rule, evaluate:\n"
    "1. **Clarity**: Is the rule unambiguous?\n"
    "2. **Completeness**: Are there gaps or edge cases?\n"
    "3. **Conflicts**: Do any rules conflict with each other?\n"
    "4. **Actionability**: Is the rule specific enough?\n"
    "\n"
    "Be concise and constructive."
)


async def auto_mode_critique_handler(model: Optional[str] = None) -> None:
    """Use the model to critique the user's custom auto-mode rules."""
    from ...query_engine import QueryEngine
    from ...api.client import VivianClient
    import json

    config = get_auto_mode_config()
    if not config or not any(config.get(k) for k in ("allow", "soft_deny", "environment")):
        print("No custom auto-mode rules found in config.json.")
        print("Set 'autoModeRules' in ~/.vivian/config.json first.")
        return

    prompt = (
        "Please review these custom auto-mode rules and provide concise feedback:\n\n"
        + json.dumps(config, indent=2)
    )
    cfg_path = Path.home() / ".vivian" / "config.json"
    try:
        full_cfg = json.loads(cfg_path.read_text())
    except Exception:
        full_cfg = {}
    api_url = full_cfg.get("api_url", "https://api-vivian.d0a.net/v1")
    api_key = full_cfg.get("api_key", "")
    used_model = model or full_cfg.get("model", "qwen3.6:latest")
    client = VivianClient(base_url=api_url, api_key=api_key)
    async for chunk in client.stream_chat(
        messages=[
            {"role": "system", "content": CRITIQUE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        model=used_model,
    ):
        text = chunk.get("content", "")
        if text:
            print(text, end="", flush=True)
    print()

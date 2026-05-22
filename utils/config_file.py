"""Configuration management — loads/saves ~/.vivian/config.json."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional


CONFIG_DIR = Path.home() / ".vivian"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    # ── Vivian server (default provider) ──────────────────────────────────
    "api_url": "https://api-vivian.d0a.net/v1",
    "api_key": "",
    "username": "",
    "model": "qwen3.6:latest",
    # ── Multi-provider settings ────────────────────────────────────────────
    # "provider" selects which AI backend to use.  Set to any id from
    # api/providers/registry.py  (e.g. "ollama", "groq", "openai", …).
    # Leaving it unset (or "vivian") preserves the existing Vivian behaviour.
    "provider": "vivian",
    # Per-provider API keys — keyed by provider id.
    # Example:  {"groq": "gsk_…", "openai": "sk-…", "mistral": "…"}
    "provider_keys": {},
    # Per-provider custom base URLs (overrides the built-in default).
    # Useful for self-hosted Ollama on a non-standard port, etc.
    # Example:  {"ollama": "http://192.168.1.10:11434/v1"}
    "provider_urls": {},
    # Per-provider default model overrides.
    # Example:  {"groq": "llama-3.1-8b-instant", "ollama": "phi3"}
    "provider_models": {},
    # ── General ────────────────────────────────────────────────────────────
    "max_turns": 25,
    "max_budget_usd": None,
    "permission_mode": "default",
    "theme": "dark",
    "vim_enabled": False,
    "buddy_enabled": True,
    "verbose": False,
    "debug": False,
}


def _ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    """Load config from ~/.vivian/config.json, merging with defaults."""
    _ensure_dir()
    config = dict(DEFAULT_CONFIG)

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                user_config = json.load(f)
            config.update(user_config)
        except (json.JSONDecodeError, OSError):
            pass

    # Also check env vars (they override file)
    if os.environ.get("VIVIAN_API_KEY"):
        config["api_key"] = os.environ["VIVIAN_API_KEY"]
    if os.environ.get("VIVIAN_API_URL"):
        config["api_url"] = os.environ["VIVIAN_API_URL"]
    if os.environ.get("VIVIAN_USERNAME"):
        config["username"] = os.environ["VIVIAN_USERNAME"]
    if os.environ.get("VIVIAN_MODEL"):
        config["model"] = os.environ["VIVIAN_MODEL"]
    if os.environ.get("VIVIAN_PROVIDER"):
        config["provider"] = os.environ["VIVIAN_PROVIDER"]

    # Inject per-provider keys from environment into config["provider_keys"]
    _PROVIDER_ENV_KEYS: dict[str, str] = {
        "openai":      "OPENAI_API_KEY",
        "anthropic":   "ANTHROPIC_API_KEY",
        "groq":        "GROQ_API_KEY",
        "gemini":      "GEMINI_API_KEY",
        "mistral":     "MISTRAL_API_KEY",
        "openrouter":  "OPENROUTER_API_KEY",
        "together":    "TOGETHER_API_KEY",
        "perplexity":  "PERPLEXITY_API_KEY",
        "huggingface": "HF_TOKEN",
        "cohere":      "COHERE_API_KEY",
    }
    if not isinstance(config.get("provider_keys"), dict):
        config["provider_keys"] = {}
    for provider_id, env_name in _PROVIDER_ENV_KEYS.items():
        val = os.environ.get(env_name)
        if val and not config["provider_keys"].get(provider_id):
            config["provider_keys"][provider_id] = val

    return config


def save_config(config: dict[str, Any]) -> None:
    """Save config to ~/.vivian/config.json."""
    _ensure_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def is_first_launch() -> bool:
    """Return True if no config file exists yet or setup_complete is not set.

    This is the trigger for the first-launch setup wizard.
    """
    if not CONFIG_FILE.exists():
        return True
    try:
        with open(CONFIG_FILE) as f:
            data = json.load(f)
        return not data.get("setup_complete", False)
    except (json.JSONDecodeError, OSError):
        return True


def write_initial_config(
    api_url: str,
    api_key: str,
    username: str,
    model: str = "qwen3.6:latest",
) -> None:
    """Write the initial config file with user credentials."""
    config = dict(DEFAULT_CONFIG)
    config["api_url"] = api_url
    config["api_key"] = api_key
    config["username"] = username
    config["model"] = model
    save_config(config)

"""AI provider registry for Vivian CLI.

Each entry describes one supported AI backend.  The "vivian" provider is
the default and preserves the existing connection behaviour unchanged.

Auth styles
-----------
bearer      Authorization: Bearer <key>   (OpenAI-compatible, most providers)
x-api-key   x-api-key: <key>              (Anthropic native)
none        No auth header                (local Ollama)
gemini      ?key=<key> query-param        (Google Gemini REST)
"""

from __future__ import annotations

import os
from typing import Any


# ── Provider catalogue ──────────────────────────────────────────────────────

PROVIDERS: dict[str, dict[str, Any]] = {

    # ── Default ─────────────────────────────────────────────────────────────
    "vivian": {
        "name":           "Vivian (default)",
        "base_url":       None,               # read from config["api_url"]
        "auth_style":     "bearer",
        "extra_headers":  {},
        "default_models": ["qwen3.6:latest", "vivian-sonnet-4-20250514"],
        "free":           True,
        "requires_key":   False,
        "note":           "Vivian's built-in server — no extra setup needed",
        "env_key":        "VIVIAN_API_KEY",
        "env_url":        "VIVIAN_API_URL",
        "key_config_key": "api_key",
        "url_config_key": "api_url",
    },

    # ── Local ────────────────────────────────────────────────────────────────
    "ollama": {
        "name":           "Ollama (local, free)",
        "base_url":       "http://localhost:11434/v1",
        "auth_style":     "none",
        "extra_headers":  {},
        "default_models": [
            "llama3.2", "llama3.1:8b", "mistral", "codellama",
            "phi3", "qwen2.5-coder:7b", "deepseek-r1",
        ],
        "free":           True,
        "requires_key":   False,
        "note":           "Run models locally. https://ollama.com",
        "env_key":        None,
        "env_url":        "OLLAMA_HOST",
        "key_config_key": None,
        "url_config_key": None,
    },

    # ── Anthropic-family ─────────────────────────────────────────────────────
    "anthropic": {
        "name":           "Anthropic (Claude direct)",
        "base_url":       "https://api.anthropic.com",
        "auth_style":     "x-api-key",
        "extra_headers":  {"anthropic-version": "2023-06-01"},
        "default_models": [
            "claude-opus-4-5-20251101",
            "claude-sonnet-4-5-20251101",
            "claude-3-5-haiku-20241022",
        ],
        "free":           False,
        "requires_key":   True,
        "note":           "Direct Anthropic API. https://console.anthropic.com",
        "env_key":        "ANTHROPIC_API_KEY",
        "env_url":        None,
        "key_config_key": None,
        "url_config_key": None,
    },

    # ── OpenAI ───────────────────────────────────────────────────────────────
    "openai": {
        "name":           "OpenAI (ChatGPT)",
        "base_url":       "https://api.openai.com/v1",
        "auth_style":     "bearer",
        "extra_headers":  {},
        "default_models": ["gpt-4o", "gpt-4o-mini", "o1-mini", "o3-mini"],
        "free":           False,
        "requires_key":   True,
        "note":           "Paid. https://platform.openai.com",
        "env_key":        "OPENAI_API_KEY",
        "env_url":        None,
        "key_config_key": None,
        "url_config_key": None,
    },

    # ── Free-tier / fast inference ───────────────────────────────────────────
    "groq": {
        "name":           "Groq (free tier)",
        "base_url":       "https://api.groq.com/openai/v1",
        "auth_style":     "bearer",
        "extra_headers":  {},
        "default_models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "gemma2-9b-it",
            "mixtral-8x7b-32768",
        ],
        "free":           True,
        "requires_key":   True,
        "note":           "Fast, free tier. https://console.groq.com  (key: gsk_…)",
        "env_key":        "GROQ_API_KEY",
        "env_url":        None,
        "key_config_key": None,
        "url_config_key": None,
    },

    "mistral": {
        "name":           "Mistral AI (free tier)",
        "base_url":       "https://api.mistral.ai/v1",
        "auth_style":     "bearer",
        "extra_headers":  {},
        "default_models": [
            "open-mistral-7b",
            "open-mixtral-8x7b",
            "mistral-small-latest",
        ],
        "free":           True,
        "requires_key":   True,
        "note":           "Free tier available. https://console.mistral.ai",
        "env_key":        "MISTRAL_API_KEY",
        "env_url":        None,
        "key_config_key": None,
        "url_config_key": None,
    },

    "openrouter": {
        "name":           "OpenRouter (many free models)",
        "base_url":       "https://openrouter.ai/api/v1",
        "auth_style":     "bearer",
        "extra_headers":  {
            "HTTP-Referer": "https://vivian.ai",
            "X-Title":      "Vivian CLI",
        },
        "default_models": [
            "meta-llama/llama-3.2-3b-instruct:free",
            "google/gemma-2-9b-it:free",
            "mistralai/mistral-7b-instruct:free",
            "deepseek/deepseek-r1:free",
        ],
        "free":           True,
        "requires_key":   True,
        "note":           "Many ':free' models available. https://openrouter.ai  (key: sk-or-…)",
        "env_key":        "OPENROUTER_API_KEY",
        "env_url":        None,
        "key_config_key": None,
        "url_config_key": None,
    },

    # ── Google ───────────────────────────────────────────────────────────────
    "gemini": {
        "name":           "Google Gemini (free tier)",
        "base_url":       "https://generativelanguage.googleapis.com/v1beta/openai",
        "auth_style":     "bearer",
        "extra_headers":  {},
        "default_models": [
            "gemini-2.0-flash-exp",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ],
        "free":           True,
        "requires_key":   True,
        "note":           "Free tier via OpenAI-compat. https://aistudio.google.com  (key: AIza…)",
        "env_key":        "GEMINI_API_KEY",
        "env_url":        None,
        "key_config_key": None,
        "url_config_key": None,
    },

    # ── HuggingFace ──────────────────────────────────────────────────────────
    "huggingface": {
        "name":           "HuggingFace (free tier)",
        "base_url":       "https://api-inference.huggingface.co/v1",
        "auth_style":     "bearer",
        "extra_headers":  {},
        "default_models": [
            "HuggingFaceH4/zephyr-7b-beta",
            "mistralai/Mistral-7B-Instruct-v0.3",
            "Qwen/Qwen2.5-72B-Instruct",
        ],
        "free":           True,
        "requires_key":   True,
        "note":           "Free Inference API. https://huggingface.co/settings/tokens  (key: hf_…)",
        "env_key":        "HF_TOKEN",
        "env_url":        None,
        "key_config_key": None,
        "url_config_key": None,
    },

    # ── Other paid ───────────────────────────────────────────────────────────
    "together": {
        "name":           "Together AI",
        "base_url":       "https://api.together.xyz/v1",
        "auth_style":     "bearer",
        "extra_headers":  {},
        "default_models": [
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
        ],
        "free":           False,
        "requires_key":   True,
        "note":           "Paid (free credits on signup). https://api.together.ai",
        "env_key":        "TOGETHER_API_KEY",
        "env_url":        None,
        "key_config_key": None,
        "url_config_key": None,
    },

    "perplexity": {
        "name":           "Perplexity AI",
        "base_url":       "https://api.perplexity.ai",
        "auth_style":     "bearer",
        "extra_headers":  {},
        "default_models": [
            "llama-3.1-sonar-large-128k-online",
            "llama-3.1-sonar-small-128k-online",
        ],
        "free":           False,
        "requires_key":   True,
        "note":           "Web-augmented responses. https://perplexity.ai",
        "env_key":        "PERPLEXITY_API_KEY",
        "env_url":        None,
        "key_config_key": None,
        "url_config_key": None,
    },

    "cohere": {
        "name":           "Cohere",
        "base_url":       "https://api.cohere.ai/compatibility/v1",
        "auth_style":     "bearer",
        "extra_headers":  {},
        "default_models": ["command-r-plus", "command-r"],
        "free":           False,
        "requires_key":   True,
        "note":           "Paid (trial credits available). https://cohere.com",
        "env_key":        "COHERE_API_KEY",
        "env_url":        None,
        "key_config_key": None,
        "url_config_key": None,
    },
}


# ── Helpers ─────────────────────────────────────────────────────────────────

def get_provider_info(provider_id: str) -> dict[str, Any]:
    """Return the registry entry for *provider_id*, or raise KeyError."""
    if provider_id not in PROVIDERS:
        known = ", ".join(sorted(PROVIDERS))
        raise KeyError(f"Unknown provider '{provider_id}'. Known: {known}")
    return PROVIDERS[provider_id]


def resolve_client_config(config: dict[str, Any], provider_id: str) -> dict[str, Any]:
    """Resolve base_url, api_key, auth_style and extra_headers for *provider_id*.

    Returns a dict with keys:
        base_url        str
        api_key         str | None
        auth_style      str
        extra_headers   dict[str, str]
        default_model   str | None
    """
    info = get_provider_info(provider_id)

    # ── base_url ─────────────────────────────────────────────────────────
    env_url_key = info.get("env_url")
    cfg_url_key = info.get("url_config_key")

    if provider_id == "vivian":
        base_url = (
            os.environ.get("VIVIAN_API_URL")
            or config.get("api_url", "https://api-vivian.d0a.net/v1")
        )
    elif provider_id == "ollama":
        base_url = (
            os.environ.get("OLLAMA_HOST", "").rstrip("/") + "/v1"
            if os.environ.get("OLLAMA_HOST")
            else config.get("provider_urls", {}).get("ollama", info["base_url"])
        )
    else:
        base_url = (
            config.get("provider_urls", {}).get(provider_id)
            or info["base_url"]
        )

    # ── api_key ──────────────────────────────────────────────────────────
    cfg_key_key = info.get("key_config_key")
    env_key_name = info.get("env_key")

    if provider_id == "vivian":
        api_key = (
            os.environ.get("VIVIAN_API_KEY")
            or config.get("api_key")
        )
    elif info.get("auth_style") == "none":
        api_key = None
    else:
        api_key = (
            (os.environ.get(env_key_name) if env_key_name else None)
            or config.get("provider_keys", {}).get(provider_id)
        )

    # ── default model ────────────────────────────────────────────────────
    default_model = (
        config.get("provider_models", {}).get(provider_id)
        or (info["default_models"][0] if info["default_models"] else None)
    )

    return {
        "base_url":      base_url,
        "api_key":       api_key,
        "auth_style":    info["auth_style"],
        "extra_headers": dict(info.get("extra_headers", {})),
        "default_model": default_model,
    }


def list_providers_text(current: str = "vivian") -> str:
    """Return a formatted table of all providers for terminal display."""
    lines = [
        "Available AI providers:",
        "",
        f"  {'ID':<14} {'FREE':^4}  {'NAME':<36} NOTE",
        "  " + "-" * 80,
    ]
    for pid, info in PROVIDERS.items():
        marker = " *" if pid == current else "  "
        free   = "yes " if info["free"] else "    "
        lines.append(f"{marker}{pid:<14} {free}  {info['name']:<36} {info['note']}")

    lines += [
        "",
        f"  Current provider: {current}",
        "",
        "  Switch with: /provider use <id>",
        "  Set key with: /provider set-key <id> <key>",
        "  Tip: set GROQ_API_KEY / OPENAI_API_KEY / etc. env vars as an alternative",
    ]
    return "\n".join(lines)

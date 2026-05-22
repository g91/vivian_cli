"""First-launch interactive setup wizard for Vivian CLI.

Runs automatically when ~/.vivian/config.json does not exist (or when
setup_complete is False).  Guides the user through choosing an AI
provider and entering the necessary credentials.

No third-party dependencies — only stdlib (sys, os, getpass, textwrap).
"""

from __future__ import annotations

import getpass
import os
import sys
import textwrap
from typing import Any

# ── ANSI colour helpers (degrade gracefully on dumb terminals) ──────────────

_USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text


def bold(t: str) -> str:     return _c("1", t)
def dim(t: str) -> str:      return _c("2", t)
def green(t: str) -> str:    return _c("32", t)
def yellow(t: str) -> str:   return _c("33", t)
def cyan(t: str) -> str:     return _c("36", t)
def magenta(t: str) -> str:  return _c("35", t)
def red(t: str) -> str:      return _c("31", t)
def blue(t: str) -> str:     return _c("34", t)
def grey(t: str) -> str:     return _c("90", t)


def _hr(char: str = "─", width: int = 60) -> None:
    print(grey(char * width))


def _clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _pause(msg: str = "Press Enter to continue…") -> None:
    try:
        input(grey(f"\n  {msg}"))
    except (EOFError, KeyboardInterrupt):
        pass


# ── Provider catalogue (mirrors api/providers/registry.py) ─────────────────
# Kept inline so the wizard has zero internal imports at call time.

_PROVIDERS: list[dict[str, Any]] = [
    {
        "id":           "vivian",
        "name":         "Vivian  (built-in default)",
        "short":        "Vivian server",
        "free":         True,
        "auth":         "api_key",
        "note":         "Vivian's own multi-model server — no extra sign-up needed.",
        "key_label":    "Vivian API key",
        "key_env":      "VIVIAN_API_KEY",
        "key_hint":     "viv-xxxxxxxxxxxxxxxx",
        "url_label":    "Server URL",
        "url_default":  "https://api-vivian.d0a.net/v1",
        "extra_fields": ["username"],
    },
    {
        "id":           "ollama",
        "name":         "Ollama  (local, 100% free)",
        "short":        "Ollama local",
        "free":         True,
        "auth":         "none",
        "note":         "Run open-source models locally. Download at https://ollama.com",
        "key_label":    None,
        "key_env":      None,
        "key_hint":     None,
        "url_label":    "Ollama host URL",
        "url_default":  "http://localhost:11434",
        "extra_fields": [],
    },
    {
        "id":           "groq",
        "name":         "Groq    (free tier — very fast)",
        "short":        "Groq",
        "free":         True,
        "auth":         "bearer",
        "note":         "Free API with extremely fast inference. Sign up at https://console.groq.com",
        "key_label":    "Groq API key",
        "key_env":      "GROQ_API_KEY",
        "key_hint":     "gsk_…",
        "url_label":    None,
        "url_default":  None,
        "extra_fields": [],
    },
    {
        "id":           "gemini",
        "name":         "Google Gemini  (free tier)",
        "short":        "Google Gemini",
        "free":         True,
        "auth":         "bearer",
        "note":         "Free tier via Google AI Studio. Get key at https://aistudio.google.com",
        "key_label":    "Gemini API key",
        "key_env":      "GEMINI_API_KEY",
        "key_hint":     "AIzaSy…",
        "url_label":    None,
        "url_default":  None,
        "extra_fields": [],
    },
    {
        "id":           "openrouter",
        "name":         "OpenRouter  (many free models)",
        "short":        "OpenRouter",
        "free":         True,
        "auth":         "bearer",
        "note":         "Access 200+ models — many ':free'. Sign up at https://openrouter.ai",
        "key_label":    "OpenRouter API key",
        "key_env":      "OPENROUTER_API_KEY",
        "key_hint":     "sk-or-v1-…",
        "url_label":    None,
        "url_default":  None,
        "extra_fields": [],
    },
    {
        "id":           "mistral",
        "name":         "Mistral AI  (free tier)",
        "short":        "Mistral",
        "free":         True,
        "auth":         "bearer",
        "note":         "European AI with strong coding models. https://console.mistral.ai",
        "key_label":    "Mistral API key",
        "key_env":      "MISTRAL_API_KEY",
        "key_hint":     "your-mistral-key",
        "url_label":    None,
        "url_default":  None,
        "extra_fields": [],
    },
    {
        "id":           "huggingface",
        "name":         "HuggingFace  (free tier)",
        "short":        "HuggingFace",
        "free":         True,
        "auth":         "bearer",
        "note":         "Access thousands of open models via HF Inference API. https://huggingface.co",
        "key_label":    "HuggingFace token",
        "key_env":      "HF_TOKEN",
        "key_hint":     "hf_…",
        "url_label":    None,
        "url_default":  None,
        "extra_fields": [],
    },
    {
        "id":           "anthropic",
        "name":         "Anthropic  (Claude — paid)",
        "short":        "Anthropic (Claude)",
        "free":         False,
        "auth":         "x-api-key",
        "note":         "Direct access to Claude 3/4 models. https://console.anthropic.com",
        "key_label":    "Anthropic API key",
        "key_env":      "ANTHROPIC_API_KEY",
        "key_hint":     "sk-ant-api03-…",
        "url_label":    None,
        "url_default":  None,
        "extra_fields": [],
    },
    {
        "id":           "openai",
        "name":         "OpenAI  (ChatGPT — paid)",
        "short":        "OpenAI",
        "free":         False,
        "auth":         "bearer",
        "note":         "GPT-4o, o1, o3 and more. https://platform.openai.com",
        "key_label":    "OpenAI API key",
        "key_env":      "OPENAI_API_KEY",
        "key_hint":     "sk-…",
        "url_label":    None,
        "url_default":  None,
        "extra_fields": [],
    },
    {
        "id":           "together",
        "name":         "Together AI  (paid, free credits)",
        "short":        "Together AI",
        "free":         False,
        "auth":         "bearer",
        "note":         "Wide model selection with free starter credits. https://api.together.ai",
        "key_label":    "Together AI API key",
        "key_env":      "TOGETHER_API_KEY",
        "key_hint":     "your-together-key",
        "url_label":    None,
        "url_default":  None,
        "extra_fields": [],
    },
    {
        "id":           "perplexity",
        "name":         "Perplexity AI  (paid)",
        "short":        "Perplexity",
        "free":         False,
        "auth":         "bearer",
        "note":         "Real-time web-augmented answers. https://perplexity.ai",
        "key_label":    "Perplexity API key",
        "key_env":      "PERPLEXITY_API_KEY",
        "key_hint":     "pplx-…",
        "url_label":    None,
        "url_default":  None,
        "extra_fields": [],
    },
    {
        "id":           "cohere",
        "name":         "Cohere  (paid, trial credits)",
        "short":        "Cohere",
        "free":         False,
        "auth":         "bearer",
        "note":         "Specialised in enterprise NLP / RAG. https://cohere.com",
        "key_label":    "Cohere API key",
        "key_env":      "COHERE_API_KEY",
        "key_hint":     "your-cohere-key",
        "url_label":    None,
        "url_default":  None,
        "extra_fields": [],
    },
]

_DEFAULT_MODELS: dict[str, list[str]] = {
    "vivian":       ["qwen3.6:latest", "vivian-sonnet-4-20250514"],
    "ollama":       ["llama3.2", "llama3.1:8b", "mistral", "codellama", "phi3",
                     "qwen2.5-coder:7b", "deepseek-r1", "gemma3:12b"],
    "groq":         ["llama-3.3-70b-versatile", "llama-3.1-8b-instant",
                     "gemma2-9b-it", "mixtral-8x7b-32768"],
    "gemini":       ["gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-pro"],
    "openrouter":   ["meta-llama/llama-3.2-3b-instruct:free",
                     "google/gemma-2-9b-it:free",
                     "deepseek/deepseek-r1:free",
                     "mistralai/mistral-7b-instruct:free"],
    "mistral":      ["open-mistral-7b", "open-mixtral-8x7b", "mistral-small-latest"],
    "huggingface":  ["HuggingFaceH4/zephyr-7b-beta",
                     "mistralai/Mistral-7B-Instruct-v0.3",
                     "Qwen/Qwen2.5-72B-Instruct"],
    "anthropic":    ["claude-opus-4-5-20251101", "claude-sonnet-4-5-20251101",
                     "claude-3-5-haiku-20241022"],
    "openai":       ["gpt-4o", "gpt-4o-mini", "o1-mini", "o3-mini"],
    "together":     ["meta-llama/Llama-3.3-70B-Instruct-Turbo",
                     "mistralai/Mixtral-8x7B-Instruct-v0.1"],
    "perplexity":   ["llama-3.1-sonar-large-128k-online",
                     "llama-3.1-sonar-small-128k-online"],
    "cohere":       ["command-r-plus", "command-r"],
}


# ── Internal input helpers ───────────────────────────────────────────────────

def _prompt(label: str, default: str = "", secret: bool = False) -> str:
    """Prompt for a value with an optional default.  Returns stripped input."""
    suffix = f" [{dim(default)}]" if default else ""
    prompt_str = f"  {cyan('›')} {bold(label)}{suffix}: "
    try:
        if secret:
            val = getpass.getpass(prompt_str)
        else:
            val = input(prompt_str)
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return val.strip() or default


def _choose(items: list[str], label: str = "Choice") -> int:
    """Present a numbered menu; return 0-based index of chosen item."""
    while True:
        raw = _prompt(label)
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(items):
                return idx
        except ValueError:
            pass
        print(red(f"  Please enter a number between 1 and {len(items)}."))


def _yes_no(question: str, default: bool = True) -> bool:
    """Ask a yes/no question."""
    hint = "[Y/n]" if default else "[y/N]"
    raw = _prompt(f"{question} {hint}", "").lower()
    if not raw:
        return default
    return raw.startswith("y")


# ── Main wizard ──────────────────────────────────────────────────────────────

def run_setup_wizard() -> dict[str, Any]:
    """Run the interactive first-launch setup wizard.

    Returns a config dict suitable for passing to ``save_config()``.
    """
    _clear()

    # ── Welcome banner ───────────────────────────────────────────────────
    print()
    print(cyan("  ╔══════════════════════════════════════════════════════════╗"))
    print(cyan("  ║") + bold(magenta("         ✦  VIVIAN CLI — First-Launch Setup Wizard  ✦        ")) + cyan("║"))
    print(cyan("  ╚══════════════════════════════════════════════════════════╝"))
    print()
    print(textwrap.dedent(f"""
  Welcome!  This wizard will configure your AI provider so Vivian
  knows how to connect.  You can change any setting later with the
  {cyan('/provider')} command inside the REPL.
    """).rstrip())
    print()
    _hr()

    # ── Step 1: choose provider ───────────────────────────────────────────
    print()
    print(bold("  Step 1 — Choose your AI provider"))
    print()

    free_label  = green(" FREE")
    paid_label  = yellow(" paid")

    for i, p in enumerate(_PROVIDERS, 1):
        tier = free_label if p["free"] else paid_label
        print(f"  {bold(cyan(str(i).rjust(2)))}. {p['name']}{tier}")

    print()
    provider_idx = _choose([p["id"] for p in _PROVIDERS], "Select provider (number)")
    provider = _PROVIDERS[provider_idx]
    pid = provider["id"]

    print()
    print(f"  {green('✔')} Selected: {bold(provider['short'])}")
    print(f"  {dim(provider['note'])}")
    print()
    _hr()

    # ── Step 2: credentials ───────────────────────────────────────────────
    print()
    print(bold(f"  Step 2 — {provider['short']} credentials"))
    print()

    cfg: dict[str, Any] = {
        "provider":        pid,
        "provider_keys":   {},
        "provider_urls":   {},
        "provider_models": {},
        "setup_complete":  True,
    }

    # ── API key (most providers) ─────────────────────────────────────────
    if provider["auth"] != "none" and provider["key_label"]:
        env_val = os.environ.get(provider["key_env"] or "", "")
        if env_val:
            print(f"  {green('✔')} Found {provider['key_env']} in environment — using it.")
            api_key = env_val
        else:
            print(f"  You need a {bold(provider['key_label'])} to use this provider.")
            print(f"  {dim(provider['note'])}")
            print()
            api_key = _prompt(provider["key_label"], provider["key_hint"] or "", secret=True)

        if pid == "vivian":
            cfg["api_key"] = api_key
        else:
            cfg["provider_keys"][pid] = api_key

    # ── Server URL (Vivian + Ollama) ─────────────────────────────────────
    if provider["url_label"]:
        print()
        print(f"  {bold(provider['url_label'])} — press Enter to use the default.")
        url = _prompt(provider["url_label"], provider["url_default"] or "")
        if pid == "vivian":
            cfg["api_url"] = url or provider["url_default"]
        else:
            if url and url != provider["url_default"]:
                cfg["provider_urls"][pid] = url

    # ── Vivian-specific: username ────────────────────────────────────────
    if "username" in provider.get("extra_fields", []):
        print()
        uname = _prompt("Username (optional, used for per-user memory)", "")
        cfg["username"] = uname

    # ── Ollama: quick model check ────────────────────────────────────────
    if pid == "ollama":
        print()
        print(f"  {bold('Ollama tips:')}")
        print(f"    • Make sure Ollama is running: {cyan('ollama serve')}")
        print(f"    • Pull a model first: {cyan('ollama pull llama3.2')}")
        print(f"    • Then set the model below or type it in the REPL with {cyan('/model llama3.2')}")

    print()
    _hr()

    # ── Step 3: model selection ────────────────────────────────────────────
    print()
    print(bold("  Step 3 — Default model"))
    print()

    models = _DEFAULT_MODELS.get(pid, [])
    if models:
        print(f"  Popular models for {bold(provider['short'])}:")
        for i, m in enumerate(models, 1):
            print(f"  {cyan(str(i).rjust(2))}. {m}")
        print(f"  {cyan(str(len(models)+1))}. Enter a custom model name")
        print()

        raw = _prompt("Select model (number or name)", "1")
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(models):
                chosen_model = models[idx]
            elif idx == len(models):
                chosen_model = _prompt("Model name", models[0])
            else:
                chosen_model = models[0]
        except ValueError:
            # User typed a model name directly
            chosen_model = raw if raw else models[0]
    else:
        chosen_model = _prompt("Model name", "")

    if chosen_model:
        cfg["provider_models"][pid] = chosen_model
        cfg["model"] = chosen_model

    print()
    print(f"  {green('✔')} Model: {bold(chosen_model or '(default)')}")
    print()
    _hr()

    # ── Step 4: optional settings ──────────────────────────────────────────
    print()
    print(bold("  Step 4 — Optional settings"))
    print()

    # Theme
    theme = "dark"
    if _yes_no("Use dark theme?", default=True):
        theme = "dark"
    else:
        theme = "light"
    cfg["theme"] = theme

    # Buddy
    buddy = _yes_no("Enable the animated buddy companion?", default=True)
    cfg["buddy_enabled"] = buddy

    print()
    _hr()

    # ── Summary ────────────────────────────────────────────────────────────
    print()
    print(bold(green("  ✓  Setup complete!  Here's your configuration:")))
    print()
    print(f"  Provider : {bold(cyan(pid))} — {provider['short']}")
    print(f"  Model    : {bold(chosen_model or '(provider default)')}")
    if pid == "vivian":
        print(f"  Server   : {cfg.get('api_url', '')}")
        if cfg.get("username"):
            print(f"  Username : {cfg['username']}")
    elif pid == "ollama":
        print(f"  Host     : {cfg['provider_urls'].get('ollama', 'http://localhost:11434')}")
    print(f"  Theme    : {theme}")
    print(f"  Buddy    : {'yes' if buddy else 'no'}")
    print()

    # Key security reminder
    if cfg.get("provider_keys") or cfg.get("api_key"):
        print(f"  {yellow('ℹ')}  Your API key has been saved to {bold('~/.vivian/config.json')}.")
        print(f"     Keep that file private (mode 600 recommended).")
        print()

    print(f"  {grey('Tip:')} run {cyan('/provider')} at any time to switch providers.")
    print(f"        run {cyan('/provider set-key <id> <key>')} to add more keys.")
    print()

    _pause("Press Enter to launch Vivian…")
    _clear()

    # Merge in remaining defaults (max_turns, permission_mode, etc.)
    defaults = {
        "api_url":        "https://api-vivian.d0a.net/v1",
        "api_key":        "",
        "username":       "",
        "max_turns":      25,
        "max_budget_usd": None,
        "permission_mode":"default",
        "vim_enabled":    False,
        "verbose":        False,
        "debug":          False,
    }
    for k, v in defaults.items():
        cfg.setdefault(k, v)

    return cfg

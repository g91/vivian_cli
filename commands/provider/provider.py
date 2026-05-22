"""``/provider`` — view and switch the active AI provider.

Usage
-----
  /provider                     Show current provider + all available
  /provider list                Same as above
  /provider use <id>            Switch to a different provider
  /provider set-key <id> <key>  Store an API key for a provider
  /provider set-url <id> <url>  Override the base URL for a provider
  /provider set-model <id> <m>  Set the default model for a provider
  /provider info <id>           Show details for one provider
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


async def call(args: str, context=None) -> str:  # noqa: C901  (complex but readable)
    """Handle /provider [sub-command] [args…]."""
    from ...api.providers.registry import PROVIDERS, list_providers_text, get_provider_info

    parts = args.strip().split() if args.strip() else []

    # ── /provider  or  /provider list ────────────────────────────────────
    if not parts or parts[0] in ("list", "ls"):
        current = "vivian"
        if context is not None:
            current = getattr(context, "config", {}).get("provider", "vivian")
        return list_providers_text(current)

    sub = parts[0].lower()

    # ── /provider info <id> ───────────────────────────────────────────────
    if sub == "info":
        if len(parts) < 2:
            return "Usage: /provider info <provider-id>"
        pid = parts[1].lower()
        try:
            info = get_provider_info(pid)
        except KeyError as exc:
            return str(exc)
        lines = [
            f"Provider: {info['name']}",
            f"  ID:             {pid}",
            f"  Base URL:       {info.get('base_url') or '(from config api_url)'}",
            f"  Auth style:     {info['auth_style']}",
            f"  Free tier:      {'yes' if info['free'] else 'no'}",
            f"  Requires key:   {'yes' if info['requires_key'] else 'no'}",
            f"  Env var:        {info.get('env_key') or '—'}",
            f"  Default models: {', '.join(info['default_models'][:3])}",
            f"  Note:           {info['note']}",
        ]
        return "\n".join(lines)

    # ── /provider use <id> ────────────────────────────────────────────────
    if sub == "use":
        if len(parts) < 2:
            return "Usage: /provider use <provider-id>"
        pid = parts[1].lower()
        try:
            info = get_provider_info(pid)
        except KeyError as exc:
            return str(exc)

        if context is None:
            return f"Cannot switch provider — no CLI context available."

        old_provider = context.config.get("provider", "vivian")
        context.set_setting("provider", pid)

        # Also update the active client so the change takes effect immediately
        _apply_provider(context, pid)

        msg = f"Switched provider: {old_provider} → {pid} ({info['name']})"
        if info["requires_key"] and not _has_key(context, pid):
            msg += (
                f"\n  No API key found for '{pid}'."
                f"\n  Set it with: /provider set-key {pid} <your-key>"
                f"\n  Or export {info.get('env_key', 'the env var')} before launching."
            )
        return msg

    # ── /provider set-key <id> <key> ─────────────────────────────────────
    if sub == "set-key":
        if len(parts) < 3:
            return "Usage: /provider set-key <provider-id> <api-key>"
        pid  = parts[1].lower()
        key  = parts[2]
        try:
            get_provider_info(pid)
        except KeyError as exc:
            return str(exc)
        if context is None:
            return "Cannot save key — no CLI context available."

        provider_keys = dict(context.config.get("provider_keys") or {})
        provider_keys[pid] = key
        context.set_setting("provider_keys", provider_keys)

        # Re-apply provider in case it's already active
        if context.config.get("provider") == pid:
            _apply_provider(context, pid)

        return f"API key saved for '{pid}'."

    # ── /provider set-url <id> <url> ─────────────────────────────────────
    if sub == "set-url":
        if len(parts) < 3:
            return "Usage: /provider set-url <provider-id> <base-url>"
        pid  = parts[1].lower()
        url  = parts[2]
        try:
            get_provider_info(pid)
        except KeyError as exc:
            return str(exc)
        if context is None:
            return "Cannot save URL — no CLI context available."

        provider_urls = dict(context.config.get("provider_urls") or {})
        provider_urls[pid] = url
        context.set_setting("provider_urls", provider_urls)

        if context.config.get("provider") == pid:
            _apply_provider(context, pid)

        return f"Custom URL saved for '{pid}': {url}"

    # ── /provider set-model <id> <model> ─────────────────────────────────
    if sub == "set-model":
        if len(parts) < 3:
            return "Usage: /provider set-model <provider-id> <model-name>"
        pid   = parts[1].lower()
        model = parts[2]
        try:
            get_provider_info(pid)
        except KeyError as exc:
            return str(exc)
        if context is None:
            return "Cannot save model — no CLI context available."

        provider_models = dict(context.config.get("provider_models") or {})
        provider_models[pid] = model
        context.set_setting("provider_models", provider_models)

        if context.config.get("provider") == pid:
            _apply_provider(context, pid)

        return f"Default model for '{pid}' set to: {model}"

    return (
        f"Unknown sub-command '{sub}'.\n"
        "Usage: /provider [list | use <id> | set-key <id> <key> | "
        "set-url <id> <url> | set-model <id> <model> | info <id>]"
    )


# ── Internal helpers ─────────────────────────────────────────────────────────

def _has_key(context, provider_id: str) -> bool:
    """Return True if a key is configured for *provider_id*."""
    from ...api.providers.registry import PROVIDERS
    import os
    info = PROVIDERS[provider_id]
    env_key = info.get("env_key")
    if env_key and os.environ.get(env_key):
        return True
    if context.config.get("provider_keys", {}).get(provider_id):
        return True
    return False


def _apply_provider(context, provider_id: str) -> None:
    """Reconfigure the active VivianClient to use *provider_id*."""
    from ...api.providers.registry import resolve_client_config
    from ...api.client import VivianClient

    resolved = resolve_client_config(context.config, provider_id)

    try:
        # Close the old httpx client if open
        import asyncio
        loop = asyncio.get_event_loop()
        if not loop.is_closed():
            loop.run_until_complete(context.client.close())
    except Exception:
        pass

    context.client = VivianClient(
        api_key=resolved["api_key"],
        base_url=resolved["base_url"],
        default_model=resolved["default_model"] or context.model,
        auth_style=resolved["auth_style"],
        extra_headers=resolved["extra_headers"],
    )
    # Invalidate the cached query engine so it picks up the new client
    context._engine = None

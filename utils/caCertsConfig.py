"""
Port of src/utils/caCertsConfig.ts
"""
from __future__ import annotations

import os

from .config import get_global_config
from .debug import log_for_debugging
from .settings.settings import getSettingsForSource


def applyExtraCACertsFromConfig():
    """Apply NODE_EXTRA_CA_CERTS from settings.json to process.env early in init,
BEFORE any TLS connections are made.

Bun caches the TLS certificate store at process boot via BoringSSL.
If NODE_EXTRA_CA_CERTS isn't set in the environment at boot, Bun won't
include the custom CA cert. By setting it on process.env before any
TLS connections, we give Bun a chance to pick it up (if the cert store
is lazy-initialized) and ensure Node.js compatibility.

This is safe to call before the trust dialog because we only read from
user-controlled files (~/.vivian/settings.json and ~/.vivian.json),
not from project-level settings."""
    if os.environ.get("NODE_EXTRA_CA_CERTS"):
        return
    config_path = getExtraCertsPathFromConfig()
    if config_path:
        os.environ["NODE_EXTRA_CA_CERTS"] = config_path
        log_for_debugging(
            f"CA certs: Applied NODE_EXTRA_CA_CERTS from config to process.env: {config_path}"
        )


def getExtraCertsPathFromConfig():
    """Read NODE_EXTRA_CA_CERTS from settings/config as a fallback.

NODE_EXTRA_CA_CERTS is categorized as a non-safe env var (it allows
trusting attacker-controlled servers), so it's only applied to process.env
after the trust dialog. But we need the CA cert early to establish the TLS
connection to an HTTPS proxy during init().

We read from global config (~/.vivian.json) and user settings
(~/.vivian/settings.json). These are user-controlled files that don't
require trust approval."""
    try:
        global_config = get_global_config() or {}
        global_env = global_config.get("env") if isinstance(global_config, dict) else None
        settings = getSettingsForSource("userSettings") or {}
        settings_env = settings.get("env") if isinstance(settings, dict) else None

        global_keys = ",".join(global_env.keys()) if isinstance(global_env, dict) else "none"
        settings_keys = ",".join(settings_env.keys()) if isinstance(settings_env, dict) else "none"
        log_for_debugging(
            f"CA certs: Config fallback - globalEnv keys: {global_keys}, settingsEnv keys: {settings_keys}"
        )

        path = None
        if isinstance(settings_env, dict):
            path = settings_env.get("NODE_EXTRA_CA_CERTS")
        if not path and isinstance(global_env, dict):
            path = global_env.get("NODE_EXTRA_CA_CERTS")
        if path:
            log_for_debugging(
                f"CA certs: Found NODE_EXTRA_CA_CERTS in config/settings: {path}"
            )
        return path
    except Exception as error:
        log_for_debugging(f"CA certs: Config fallback failed: {error}", level="error")
        return None


apply_extra_ca_certs_from_config = applyExtraCACertsFromConfig
get_extra_certs_path_from_config = getExtraCertsPathFromConfig


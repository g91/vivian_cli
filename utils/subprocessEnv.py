"""Subprocess environment scrubbing — mirrors src/utils/subprocessEnv.ts"""
from __future__ import annotations

import os
from typing import Callable, Optional

# Env vars to strip when spawning subprocesses inside GitHub Actions
GHA_SUBPROCESS_SCRUB = [
    "ANTHROPIC_API_KEY",
    "vivian_CODE_OAUTH_TOKEN",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_FOUNDRY_API_KEY",
    "ANTHROPIC_CUSTOM_HEADERS",
    "OTEL_EXPORTER_OTLP_HEADERS",
    "OTEL_EXPORTER_OTLP_LOGS_HEADERS",
    "OTEL_EXPORTER_OTLP_METRICS_HEADERS",
    "OTEL_EXPORTER_OTLP_TRACES_HEADERS",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_BEARER_TOKEN_BEDROCK",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "AZURE_CLIENT_SECRET",
    "AZURE_CLIENT_CERTIFICATE_PATH",
    "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
    "ACTIONS_ID_TOKEN_REQUEST_URL",
    "ACTIONS_RUNTIME_TOKEN",
    "ACTIONS_RUNTIME_URL",
    "ALL_INPUTS",
    "OVERRIDE_GITHUB_TOKEN",
    "DEFAULT_WORKFLOW_TOKEN",
    "SSH_SIGNING_KEY",
]

_upstream_proxy_env_fn: Optional[Callable[[], dict[str, str]]] = None


def register_upstream_proxy_env_fn(fn: Callable[[], dict[str, str]]) -> None:
    """Wire up the upstream proxy env function after lazy load."""
    global _upstream_proxy_env_fn
    _upstream_proxy_env_fn = fn


def subprocess_env() -> dict[str, str]:
    """Return a copy of the environment safe for subprocess use.

    Strips sensitive secrets when vivian_CODE_SUBPROCESS_ENV_SCRUB is set,
    and injects upstream proxy env vars when registered.
    """
    env = dict(os.environ)

    scrub = os.environ.get("vivian_CODE_SUBPROCESS_ENV_SCRUB")
    if scrub and scrub not in ("0", "false", "no"):
        for key in GHA_SUBPROCESS_SCRUB:
            env.pop(key, None)

    if _upstream_proxy_env_fn is not None:
        env.update(_upstream_proxy_env_fn())

    return env


def get_subprocess_env(
    extra: Optional[dict[str, str]] = None,
    *,
    clear_api_key: bool = False,
) -> dict[str, str]:
    """Build an environment dict suitable for spawning subprocesses (legacy helper)."""
    env = subprocess_env()
    if extra:
        env.update(extra)
    if clear_api_key:
        env.pop("ANTHROPIC_API_KEY", None)
    return env

"""Environment utilities — mirrors src/utils/envUtils.ts"""
from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=None)
def get_vivian_config_home_dir() -> str:
    """Return the Vivian config directory. Cached after first call.

    Reads ``vivian_CONFIG_DIR`` env var; defaults to ``~/.vivian``.
    """
    raw = os.environ.get("vivian_CONFIG_DIR")
    if raw:
        return str(Path(raw).expanduser())
    return str(Path.home() / ".vivian")


def get_teams_dir() -> str:
    """Return the teams subdirectory inside the config home."""
    return str(Path(get_vivian_config_home_dir()) / "teams")


def is_env_truthy(env_var: str | bool | None) -> bool:
    """Return True if env_var is a truthy environment variable value."""
    if not env_var:
        return False
    if isinstance(env_var, bool):
        return env_var
    return env_var.lower().strip() in ("1", "true", "yes", "on")


def is_env_defined_falsy(env_var: str | bool | None) -> bool:
    """Return True if env_var is explicitly set to a falsy value."""
    if env_var is None:
        return False
    if isinstance(env_var, bool):
        return not env_var
    if not env_var:
        return False
    return env_var.lower().strip() in ("0", "false", "no", "off")


def is_bare_mode() -> bool:
    """Return True if running in bare / simple mode (--bare flag or env)."""
    return is_env_truthy(os.environ.get("vivian_CODE_SIMPLE")) or "--bare" in sys.argv


def parse_env_vars(raw_env_args: list[str] | None) -> dict[str, str]:
    """Parse a list of ``KEY=VALUE`` strings into a dict."""
    result: dict[str, str] = {}
    if not raw_env_args:
        return result
    for entry in raw_env_args:
        parts = entry.split("=", 1)
        if len(parts) != 2 or not parts[0]:
            raise ValueError(
                f"Invalid environment variable format: {entry}, "
                "environment variables should be added as: -e KEY1=value1 -e KEY2=value2"
            )
        result[parts[0]] = parts[1]
    return result


def get_aws_region() -> str:
    """Return the AWS region, with fallback to us-east-1."""
    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"


def get_default_vertex_region() -> str:
    """Return the default Vertex AI region."""
    return os.environ.get("CLOUD_ML_REGION") or "us-east5"


def should_maintain_project_working_dir() -> bool:
    """Return True if bash commands should reset cwd after each command."""
    return is_env_truthy(os.environ.get("vivian_BASH_MAINTAIN_PROJECT_WORKING_DIR"))


def is_running_on_homespace() -> bool:
    """Return True if running on Homespace (Anthropic internal cloud)."""
    return (
        os.environ.get("USER_TYPE") == "ant"
        and bool(os.environ.get("HOMESPACE_ENV"))
    )

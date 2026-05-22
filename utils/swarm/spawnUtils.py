"""Port of src/utils/swarm/spawnUtils.ts."""
from __future__ import annotations

import os
import sys

from ...bootstrap.state import (
    getChromeFlagOverride,
    getFlagSettingsPath,
    getInlinePlugins,
    getMainLoopModelOverride,
    getSessionBypassPermissionsMode,
)
from ..bash.shellQuote import quote
from ..bundledMode import is_in_bundled_mode
from .backends.teammateModeSnapshot import getTeammateModeFromSnapshot
from .constants import TEAMMATE_COMMAND_ENV_VAR


TEAMMATE_ENV_VARS = [
    "vivian_CODE_USE_BEDROCK",
    "vivian_CODE_USE_VERTEX",
    "vivian_CODE_USE_FOUNDRY",
    "ANTHROPIC_BASE_URL",
    "vivian_CONFIG_DIR",
    "vivian_CODE_REMOTE",
    "vivian_CODE_REMOTE_MEMORY_DIR",
    "HTTPS_PROXY",
    "https_proxy",
    "HTTP_PROXY",
    "http_proxy",
    "NO_PROXY",
    "no_proxy",
    "SSL_CERT_FILE",
    "NODE_EXTRA_CA_CERTS",
    "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE",
]


def getTeammateCommand() -> str:
    override = os.environ.get(TEAMMATE_COMMAND_ENV_VAR)
    if override:
        return override
    if is_in_bundled_mode():
        return sys.executable
    return sys.argv[0] or sys.executable


def buildInheritedCliFlags(options=None) -> str:
    flags: list[str] = []
    options = options or {}
    if not isinstance(options, dict):
        options = {
            "planModeRequired": getattr(options, "planModeRequired", None),
            "permissionMode": getattr(options, "permissionMode", None),
        }

    plan_mode_required = options.get("planModeRequired")
    permission_mode = options.get("permissionMode")

    if not plan_mode_required:
        if permission_mode == "bypassPermissions" or getSessionBypassPermissionsMode():
            flags.append("--dangerously-skip-permissions")
        elif permission_mode == "acceptEdits":
            flags.append("--permission-mode acceptEdits")

    model_override = getMainLoopModelOverride()
    if model_override:
        flags.append(f"--model {quote([str(model_override)])}")

    settings_path = getFlagSettingsPath()
    if settings_path:
        flags.append(f"--settings {quote([settings_path])}")

    for plugin_dir in getInlinePlugins():
        flags.append(f"--plugin-dir {quote([plugin_dir])}")

    session_mode = getTeammateModeFromSnapshot()
    flags.append(f"--teammate-mode {session_mode}")

    chrome_flag_override = getChromeFlagOverride()
    if chrome_flag_override is True:
        flags.append("--chrome")
    elif chrome_flag_override is False:
        flags.append("--no-chrome")

    return " ".join(flags)


def buildInheritedEnvVars() -> str:
    env_vars = ["vivianCODE=1", "vivian_CODE_EXPERIMENTAL_AGENT_TEAMS=1"]
    for key in TEAMMATE_ENV_VARS:
        value = os.environ.get(key)
        if value:
            env_vars.append(f"{key}={quote([value])}")
    return " ".join(env_vars)


get_teammate_command = getTeammateCommand
build_inherited_cli_flags = buildInheritedCliFlags
build_inherited_env_vars = buildInheritedEnvVars
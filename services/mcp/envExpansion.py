"""MCP environment variable expansion — mirrors src/services/mcp/envExpansion.ts."""
from __future__ import annotations

import os
import re
from typing import NamedTuple


class ExpandResult(NamedTuple):
    expanded: str
    missing_vars: list[str]


def expandEnvVarsInString(value: str) -> ExpandResult:
    """Expand environment variables in a string value.

    Handles ${VAR} and ${VAR:-default} syntax.
    Mirrors expandEnvVarsInString() from envExpansion.ts.
    """
    missing_vars: list[str] = []

    def replace(m: re.Match) -> str:
        var_content = m.group(1)
        parts = var_content.split(":-", 1)
        var_name = parts[0]
        default_value = parts[1] if len(parts) > 1 else None

        env_value = os.environ.get(var_name)
        if env_value is not None:
            return env_value
        if default_value is not None:
            return default_value

        missing_vars.append(var_name)
        return m.group(0)  # return original

    expanded = re.sub(r"\$\{([^}]+)\}", replace, value)
    return ExpandResult(expanded=expanded, missing_vars=missing_vars)


expand_env_vars_in_string = expandEnvVarsInString

"""Port of src/utils/sessionEnvVars.ts."""
from __future__ import annotations

_session_env_vars: dict[str, str] = {}


def getSessionEnvVars():
    return list(_session_env_vars.items())


def setSessionEnvVar(name, value):
    _session_env_vars[name] = value


def deleteSessionEnvVar(name):
    _session_env_vars.pop(name, None)


def clearSessionEnvVars():
    _session_env_vars.clear()


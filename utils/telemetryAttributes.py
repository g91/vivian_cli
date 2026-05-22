"""Port of src/utils/telemetryAttributes.ts."""
from __future__ import annotations

from typing import Any, Dict
import os

from ..bootstrap.state import getSessionId
from .auth import get_vivian_ai_oauth_tokens
from .config import get_or_create_user_id
from .envDynamic import envDynamic
from .envUtils import is_env_truthy
from .taggedId import to_tagged_id


METRICS_CARDINALITY_DEFAULTS = {
    "OTEL_METRICS_INCLUDE_SESSION_ID": True,
    "OTEL_METRICS_INCLUDE_VERSION": False,
    "OTEL_METRICS_INCLUDE_ACCOUNT_UUID": True,
}


def shouldIncludeAttribute(envVar):
    defaultValue = METRICS_CARDINALITY_DEFAULTS[envVar]
    envValue = os.environ.get(envVar)
    if envValue is None:
        return defaultValue
    return isEnvTruthy(envValue)


def getTelemetryAttributes():
    user_id = get_or_create_user_id()
    session_id = getSessionId()

    attributes: Dict[str, Any] = {
        "user.id": user_id,
    }

    if shouldIncludeAttribute("OTEL_METRICS_INCLUDE_SESSION_ID"):
        attributes["session.id"] = session_id

    if shouldIncludeAttribute("OTEL_METRICS_INCLUDE_VERSION"):
        version = os.environ.get("vivian_CODE_VERSION") or os.environ.get("VIVIAN_VERSION")
        if version:
            attributes["app.version"] = version

    oauth_account = get_vivian_ai_oauth_tokens()
    if oauth_account:
        org_id = getattr(oauth_account, "organization_uuid", None)
        email = getattr(oauth_account, "email", None)
        account_uuid = getattr(oauth_account, "account_uuid", None)

        if org_id:
            attributes["organization.id"] = org_id
        if email:
            attributes["user.email"] = email
        if account_uuid and shouldIncludeAttribute("OTEL_METRICS_INCLUDE_ACCOUNT_UUID"):
            attributes["user.account_uuid"] = account_uuid
            attributes["user.account_id"] = (
                os.environ.get("vivian_CODE_ACCOUNT_TAGGED_ID")
                or to_tagged_id("user", account_uuid)
            )

    terminal = getattr(envDynamic, "terminal", None) if envDynamic is not None else None
    if terminal:
        attributes["terminal.type"] = terminal

    return attributes


isEnvTruthy = is_env_truthy
getTelemetryAttributes = getTelemetryAttributes
get_telemetry_attributes = getTelemetryAttributes

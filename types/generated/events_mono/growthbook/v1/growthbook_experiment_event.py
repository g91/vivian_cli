"""Generated from events_mono/growthbook/v1/growthbook_experiment_event.proto."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from ....google.protobuf.timestamp import Timestamp
from ...common.v1.auth import PublicApiAuth


def isSet(value: Any) -> bool:
    return value is not None


def fromTimestamp(t: Timestamp) -> datetime:
    return datetime.fromtimestamp(t.seconds + (t.nanos / 1_000_000_000))


def fromJsonTimestamp(o: Any) -> datetime:
    if isinstance(o, datetime):
        return o
    if isinstance(o, str):
        return datetime.fromisoformat(o.replace("Z", "+00:00"))
    return fromTimestamp(Timestamp.fromJSON(o))


@dataclass
class GrowthbookExperimentEvent:
    event_id: str = ""
    timestamp: Optional[datetime] = None
    experiment_id: str = ""
    variation_id: int = 0
    environment: str = ""
    user_attributes: str = ""
    experiment_metadata: str = ""
    device_id: str = ""
    auth: Optional[PublicApiAuth] = None
    session_id: str = ""
    anonymous_id: str = ""
    event_metadata_vars: str = ""

    @classmethod
    def fromJSON(cls, object: Any) -> "GrowthbookExperimentEvent":
        return cls(
            event_id=str(object.get("event_id", "")) if isSet(object.get("event_id")) else "",
            timestamp=fromJsonTimestamp(object.get("timestamp")) if isSet(object.get("timestamp")) else None,
            experiment_id=str(object.get("experiment_id", "")) if isSet(object.get("experiment_id")) else "",
            variation_id=int(object.get("variation_id", 0)) if isSet(object.get("variation_id")) else 0,
            environment=str(object.get("environment", "")) if isSet(object.get("environment")) else "",
            user_attributes=str(object.get("user_attributes", "")) if isSet(object.get("user_attributes")) else "",
            experiment_metadata=str(object.get("experiment_metadata", "")) if isSet(object.get("experiment_metadata")) else "",
            device_id=str(object.get("device_id", "")) if isSet(object.get("device_id")) else "",
            auth=PublicApiAuth.fromJSON(object.get("auth")) if isSet(object.get("auth")) else None,
            session_id=str(object.get("session_id", "")) if isSet(object.get("session_id")) else "",
            anonymous_id=str(object.get("anonymous_id", "")) if isSet(object.get("anonymous_id")) else "",
            event_metadata_vars=str(object.get("event_metadata_vars", "")) if isSet(object.get("event_metadata_vars")) else "",
        )

    @staticmethod
    def toJSON(message: "GrowthbookExperimentEvent") -> dict[str, Any]:
        obj: dict[str, Any] = {
            "event_id": message.event_id,
            "experiment_id": message.experiment_id,
            "variation_id": round(message.variation_id),
            "environment": message.environment,
            "user_attributes": message.user_attributes,
            "experiment_metadata": message.experiment_metadata,
            "device_id": message.device_id,
            "session_id": message.session_id,
            "anonymous_id": message.anonymous_id,
            "event_metadata_vars": message.event_metadata_vars,
        }
        if message.timestamp is not None:
            obj["timestamp"] = message.timestamp.isoformat().replace("+00:00", "Z")
        if message.auth is not None:
            obj["auth"] = PublicApiAuth.toJSON(message.auth)
        return obj

    @classmethod
    def create(cls, base: Optional[dict[str, Any]] = None) -> "GrowthbookExperimentEvent":
        return cls.fromPartial(base or {})

    @classmethod
    def fromPartial(cls, object: Any) -> "GrowthbookExperimentEvent":
        data = object if isinstance(object, dict) else vars(object)
        auth = data.get("auth")
        return cls(
            event_id=data.get("event_id", "") or "",
            timestamp=data.get("timestamp"),
            experiment_id=data.get("experiment_id", "") or "",
            variation_id=data.get("variation_id", 0) or 0,
            environment=data.get("environment", "") or "",
            user_attributes=data.get("user_attributes", "") or "",
            experiment_metadata=data.get("experiment_metadata", "") or "",
            device_id=data.get("device_id", "") or "",
            auth=PublicApiAuth.fromPartial(auth) if auth is not None else None,
            session_id=data.get("session_id", "") or "",
            anonymous_id=data.get("anonymous_id", "") or "",
            event_metadata_vars=data.get("event_metadata_vars", "") or "",
        )


def createBaseGrowthbookExperimentEvent() -> GrowthbookExperimentEvent:
    return GrowthbookExperimentEvent()
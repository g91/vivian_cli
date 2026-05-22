"""Generated from google/protobuf/timestamp.proto."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


def isSet(value: Any) -> bool:
    return value is not None


@dataclass
class Timestamp:
    seconds: int = 0
    nanos: int = 0

    @classmethod
    def fromJSON(cls, object: Any) -> "Timestamp":
        return cls(
            seconds=int(object.get("seconds", 0)) if isSet(object.get("seconds")) else 0,
            nanos=int(object.get("nanos", 0)) if isSet(object.get("nanos")) else 0,
        )

    @staticmethod
    def toJSON(message: "Timestamp") -> dict[str, Any]:
        return {"seconds": round(message.seconds), "nanos": round(message.nanos)}

    @classmethod
    def create(cls, base: Optional[dict[str, Any]] = None) -> "Timestamp":
        return cls.fromPartial(base or {})

    @classmethod
    def fromPartial(cls, object: Any) -> "Timestamp":
        seconds = getattr(object, "seconds", None) if not isinstance(object, dict) else object.get("seconds")
        nanos = getattr(object, "nanos", None) if not isinstance(object, dict) else object.get("nanos")
        return cls(seconds=0 if seconds is None else int(seconds), nanos=0 if nanos is None else int(nanos))


def createBaseTimestamp() -> Timestamp:
    return Timestamp()
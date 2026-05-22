"""Generated from events_mono/common/v1/auth.proto."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


def isSet(value: Any) -> bool:
    return value is not None


@dataclass
class PublicApiAuth:
    account_id: int = 0
    organization_uuid: str = ""
    account_uuid: str = ""

    @classmethod
    def fromJSON(cls, object: Any) -> "PublicApiAuth":
        return cls(
            account_id=int(object.get("account_id", 0)) if isSet(object.get("account_id")) else 0,
            organization_uuid=str(object.get("organization_uuid", "")) if isSet(object.get("organization_uuid")) else "",
            account_uuid=str(object.get("account_uuid", "")) if isSet(object.get("account_uuid")) else "",
        )

    @staticmethod
    def toJSON(message: "PublicApiAuth") -> dict[str, Any]:
        return {
            "account_id": round(message.account_id),
            "organization_uuid": message.organization_uuid,
            "account_uuid": message.account_uuid,
        }

    @classmethod
    def create(cls, base: Optional[dict[str, Any]] = None) -> "PublicApiAuth":
        return cls.fromPartial(base or {})

    @classmethod
    def fromPartial(cls, object: Any) -> "PublicApiAuth":
        return cls(
            account_id=getattr(object, "account_id", None) if not isinstance(object, dict) else object.get("account_id", 0) or 0,
            organization_uuid=getattr(object, "organization_uuid", None) if not isinstance(object, dict) else object.get("organization_uuid", "") or "",
            account_uuid=getattr(object, "account_uuid", None) if not isinstance(object, dict) else object.get("account_uuid", "") or "",
        )


def createBasePublicApiAuth() -> PublicApiAuth:
    return PublicApiAuth()
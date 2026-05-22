"""Remote managed settings types.

Mirrors src/services/remoteManagedSettings/types.ts.
"""
from __future__ import annotations

from typing import NotRequired, TypedDict

from ...utils.settings.types import SettingsJson


class RemoteManagedSettingsResponse(TypedDict):
    uuid: str
    checksum: str
    settings: SettingsJson


class RemoteManagedSettingsFetchResult(TypedDict, total=False):
    success: bool
    settings: NotRequired[SettingsJson | None]
    checksum: NotRequired[str]
    error: NotRequired[str]
    skipRetry: NotRequired[bool]

"""Port of src/hooks/useUpdateNotification.ts."""
from __future__ import annotations

import re
from typing import Optional


_SEMVER_RE = re.compile(r'^(\d+)\.(\d+)\.(\d+)')


def getSemverPart(version: str) -> str:
    m = _SEMVER_RE.match(version or '')
    if not m:
        return '0.0.0'
    return f"{int(m.group(1))}.{int(m.group(2))}.{int(m.group(3))}"


def shouldShowUpdateNotification(updatedVersion: str, lastNotifiedSemver: str | None) -> bool:
    updated_semver = getSemverPart(updatedVersion)
    return updated_semver != lastNotifiedSemver


def useUpdateNotification(updatedVersion: Optional[str], initialVersion: str = '0.0.0') -> Optional[str]:
    if not updatedVersion:
        return None
    updated_semver = getSemverPart(updatedVersion)
    initial_semver = getSemverPart(initialVersion)
    if updated_semver != initial_semver:
        return updated_semver
    return None

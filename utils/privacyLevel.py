"""
Port of src/utils/privacyLevel.ts
"""
from __future__ import annotations

import os
import os.path
from typing import Any, Optional, Union, Callable, TypeVar, List, Dict, Tuple, Set, cast, overload, TYPE_CHECKING


"""
Privacy level controls how much nonessential network traffic and telemetry
vivian Code generates.
Levels are ordered by restrictiveness:
default < no-telemetry < essential-traffic
- default:            Everything enabled.
- no-telemetry:       Analytics/telemetry disabled (Datadog, 1P events, feedback survey).
- essential-traffic:  ALL nonessential network traffic disabled
(telemetry + auto-updates, grove, release notes, model capabilities, etc.).
The resolved level is the most restrictive signal from:
vivian_CODE_DISABLE_NONESSENTIAL_TRAFFIC  →  essential-traffic
DISABLE_TELEMETRY                         →  no-telemetry
"""

PrivacyLevel = str

def getPrivacyLevel():
    if os.environ.get('vivian_CODE_DISABLE_NONESSENTIAL_TRAFFIC'):
        return 'essential-traffic'
    if os.environ.get('DISABLE_TELEMETRY'):
        return 'no-telemetry'
    return 'default'

"""
True when all nonessential network traffic should be suppressed.
Equivalent to the old `process.env.vivian_CODE_DISABLE_NONESSENTIAL_TRAFFIC` check.
"""
def isEssentialTrafficOnly():
    return getPrivacyLevel() == 'essential-traffic'

"""
True when telemetry/analytics should be suppressed.
True at both `no-telemetry` and `essential-traffic` levels.
"""
def isTelemetryDisabled():
    return getPrivacyLevel() != 'default'

"""
Returns the env var name responsible for the current essential-traffic restriction,
or null if unrestricted. Used for user-facing "unset X to re-enable" messages.
"""
def getEssentialTrafficOnlyReason():
    if os.environ.get('vivian_CODE_DISABLE_NONESSENTIAL_TRAFFIC'):
        return 'vivian_CODE_DISABLE_NONESSENTIAL_TRAFFIC'
    return None


get_privacy_level = getPrivacyLevel
is_essential_traffic_only = isEssentialTrafficOnly
is_telemetry_disabled = isTelemetryDisabled
get_essential_traffic_only_reason = getEssentialTrafficOnlyReason

"""
passpass of src/utils/autoModeDenials
"""
from __future__ import annotations

from typing import Any, Dict, List

from .classifierApprovals import feature

AutoModeDenial = Dict[str, Any]
DENIALS: List[AutoModeDenial] = []
MAX_DENIALS = 20


def recordAutoModeDenial(denial):
    global DENIALS
    if not feature('TRANSCRIPT_CLASSIFIER'):
        return None
    DENIALS = [denial, *DENIALS[: MAX_DENIALS - 1]]
    return None


def getAutoModeDenials():
    return list(DENIALS)


def resetAutoModeDenials():
    global DENIALS
    DENIALS = []


record_auto_mode_denial = recordAutoModeDenial
get_auto_mode_denials = getAutoModeDenials
reset_auto_mode_denials = resetAutoModeDenials


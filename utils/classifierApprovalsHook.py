"""
Port of src/utils/classifierApprovalsHook
"""
from __future__ import annotations

from .classifierApprovals import isClassifierChecking


def useIsClassifierChecking(toolUseID):
    return isClassifierChecking(toolUseID)


use_is_classifier_checking = useIsClassifierChecking


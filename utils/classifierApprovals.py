"""
passpasspass of src/utils/classifierApprovals
"""
from __future__ import annotations

import os
from typing import Any, Dict

from .signal import create_signal


ClassifierApproval = Dict[str, Any]


def _env_truthy(name: str) -> bool:
    value = os.environ.get(name)
    if value is None:
        return False
    return value.strip().lower() not in {"", "0", "false", "no", "off"}


def feature(name: str) -> bool:
    return _env_truthy(name.upper())


CLASSIFIER_APPROVALS: dict[str, ClassifierApproval] = {}
CLASSIFIER_CHECKING: set[str] = set()
classifierChecking = create_signal()


subscribeClassifierChecking: Any = classifierChecking.subscribe  # type: ignore


def setClassifierApproval(toolUseID, matchedRule):
    if not feature('BASH_CLASSIFIER'):
        return
    CLASSIFIER_APPROVALS[toolUseID] = {
        'classifier': 'bash',
        'matchedRule': matchedRule,
    }


def getClassifierApproval(toolUseID):
    if not feature('BASH_CLASSIFIER'):
        return None
    approval = CLASSIFIER_APPROVALS.get(toolUseID)
    if not approval or approval.get('classifier') != 'bash':
        return None
    return approval.get('matchedRule')


def setYoloClassifierApproval(toolUseID, reason):
    if not feature('TRANSCRIPT_CLASSIFIER'):
        return
    CLASSIFIER_APPROVALS[toolUseID] = {'classifier': 'auto-mode', 'reason': reason}


def getYoloClassifierApproval(toolUseID):
    if not feature('TRANSCRIPT_CLASSIFIER'):
        return None
    approval = CLASSIFIER_APPROVALS.get(toolUseID)
    if not approval or approval.get('classifier') != 'auto-mode':
        return None
    return approval.get('reason')


def setClassifierChecking(toolUseID):
    if not feature('BASH_CLASSIFIER') and not feature('TRANSCRIPT_CLASSIFIER'):
        return
    CLASSIFIER_CHECKING.add(toolUseID)
    classifierChecking.emit()


def clearClassifierChecking(toolUseID):
    if not feature('BASH_CLASSIFIER') and not feature('TRANSCRIPT_CLASSIFIER'):
        return
    CLASSIFIER_CHECKING.discard(toolUseID)
    classifierChecking.emit()


def isClassifierChecking(toolUseID):
    return toolUseID in CLASSIFIER_CHECKING


def deleteClassifierApproval(toolUseID):
    CLASSIFIER_APPROVALS.pop(toolUseID, None)


def clearClassifierApprovals():
    CLASSIFIER_APPROVALS.clear()
    CLASSIFIER_CHECKING.clear()
    classifierChecking.emit()


set_classifier_approval = setClassifierApproval
get_classifier_approval = getClassifierApproval
set_yolo_classifier_approval = setYoloClassifierApproval
get_yolo_classifier_approval = getYoloClassifierApproval
set_classifier_checking = setClassifierChecking
clear_classifier_checking = clearClassifierChecking
is_classifier_checking = isClassifierChecking
delete_classifier_approval = deleteClassifierApproval
clear_classifier_approvals = clearClassifierApprovals
subscribe_classifier_checking = subscribeClassifierChecking


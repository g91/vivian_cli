"""
Port of src/utils/autoRunIssue.tsx
"""
from __future__ import annotations

import os
from typing import Any, Dict, Literal


Props = Dict[str, Any]
AutoRunIssueReason = Literal["feedback_survey_bad", "feedback_survey_good"]

_REASON_TEXT: dict[str, str] = {
    "feedback_survey_bad": 'You responded "Bad" to the feedback survey',
    "feedback_survey_good": 'You responded "Good" to the feedback survey',
}


def AutoRunIssueNotification(t0):
    """Component that shows a notification about running /issue command
with the ability to cancel via ESC key"""
    props = t0 if isinstance(t0, dict) else dict(t0 or {})
    on_run = props.get("onRun")
    has_run_key = "_hasRun"
    if callable(on_run) and not props.get(has_run_key):
        props[has_run_key] = True
        on_run()
    return {
        "type": "auto_run_issue_notification",
        "status": "running_feedback_capture",
        "cancelShortcut": "Esc",
        "reason": props.get("reason", ""),
    }


def shouldAutoRunIssue(reason):
    """Determines if /issue should auto-run for Ant users"""
    if os.environ.get("USER_TYPE") != "ant":
        return False
    return reason in _REASON_TEXT and False


def getAutoRunCommand(reason):
    """Returns the appropriate command to auto-run based on the reason
ANT-ONLY: good-vivian command only exists in ant builds"""
    if os.environ.get("USER_TYPE") == "ant" and reason == "feedback_survey_good":
        return "/good-vivian"
    return "/issue"


def getAutoRunIssueReasonText(reason):
    """Gets a human-readable description of why /issue is being auto-run"""
    return _REASON_TEXT.get(reason, "Unknown reason")


auto_run_issue_notification = AutoRunIssueNotification
should_auto_run_issue = shouldAutoRunIssue
get_auto_run_command = getAutoRunCommand
get_auto_run_issue_reason_text = getAutoRunIssueReasonText


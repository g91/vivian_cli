"""
Port of src/utils/collapseHookSummaries.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import math


def isLabeledHookSummary(msg):
    if not isinstance(msg, dict):
        return False
    return (
        msg.get('type') == 'system' and
        msg.get('subtype') == 'stop_hook_summary' and
        msg.get('hookLabel') is not None
    )


def collapseHookSummaries(messages):
    """Collapses consecutive hook summary messages with the same hookLabel
(e.g. PostToolUse) into a single summary. This happens when parallel
tool calls each emit their own hook summary."""
    result = []
    index = 0
    messages = messages or []

    while index < len(messages):
        message = messages[index]
        if isLabeledHookSummary(message):
            label = message.get('hookLabel')
            group = []
            while index < len(messages):
                next_message = messages[index]
                if not isLabeledHookSummary(next_message) or next_message.get('hookLabel') != label:
                    break
                group.append(next_message)
                index += 1
            if len(group) == 1:
                result.append(message)
            else:
                merged = dict(message)
                merged['hookCount'] = sum(int(item.get('hookCount', 0) or 0) for item in group)
                merged['hookInfos'] = [info for item in group for info in (item.get('hookInfos') or [])]
                merged['hookErrors'] = [error for item in group for error in (item.get('hookErrors') or [])]
                merged['preventedContinuation'] = any(bool(item.get('preventedContinuation')) for item in group)
                merged['hasOutput'] = any(bool(item.get('hasOutput')) for item in group)
                merged['totalDurationMs'] = max(float(item.get('totalDurationMs', 0) or 0) for item in group)
                result.append(merged)
            continue

        result.append(message)
        index += 1

    return result


is_labeled_hook_summary = isLabeledHookSummary
collapse_hook_summaries = collapseHookSummaries


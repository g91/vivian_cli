"""
Port of src/utils/collapseBackgroundBashNotifications.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import re

from ..tasks.LocalShellTask import BACKGROUND_BASH_SUMMARY_PREFIX
from .fullscreen import isFullscreenEnvEnabled


TASK_NOTIFICATION_TAG = 'task-notification'
STATUS_TAG = 'status'
SUMMARY_TAG = 'summary'


def _extract_tag(text, tag_name):
    match = re.search(rf'<{tag_name}>(.*?)</{tag_name}>', str(text), re.DOTALL)
    return match.group(1) if match else None


def _first_text_block(msg):
    if not isinstance(msg, dict) or msg.get('type') != 'user':
        return None
    payload = msg.get('message') if isinstance(msg.get('message'), dict) else {}
    content = payload.get('content')
    if not isinstance(content, list) or not content:
        return None
    first = content[0]
    if isinstance(first, dict) and first.get('type') == 'text' and isinstance(first.get('text'), str):
        return first
    return None


def isCompletedBackgroundBash(msg):
    content = _first_text_block(msg)
    if not content:
        return False
    text = content['text']
    if f'<{TASK_NOTIFICATION_TAG}>' not in text:
        return False
    if _extract_tag(text, STATUS_TAG) != 'completed':
        return False
    summary = _extract_tag(text, SUMMARY_TAG)
    return bool(summary and summary.startswith(BACKGROUND_BASH_SUMMARY_PREFIX))


def collapseBackgroundBashNotifications(messages, verbose):
    """Collapses consecutive completed-background-bash task-notifications into a
single synthetic "N background commands completed" notification. Failed/killed
tasks and agent/workflow notifications are left alone. Monitor stream
events (enqueueStreamEvent) have no <status> tag and never match.

Pass-through in verbose mode so ctrl+O shows each completion."""
    if not isFullscreenEnvEnabled():
        return messages
    if verbose:
        return messages

    result = []
    index = 0
    while index < len(messages or []):
        message = messages[index]
        if isCompletedBackgroundBash(message):
            count = 0
            start_message = message
            while index < len(messages or []) and isCompletedBackgroundBash(messages[index]):
                count += 1
                index += 1
            if count == 1:
                result.append(start_message)
            else:
                synthetic = dict(start_message)
                synthetic['message'] = {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': (
                                f'<{TASK_NOTIFICATION_TAG}>'
                                f'<{STATUS_TAG}>completed</{STATUS_TAG}>'
                                f'<{SUMMARY_TAG}>{count} background commands completed</{SUMMARY_TAG}>'
                                f'</{TASK_NOTIFICATION_TAG}>'
                            ),
                        }
                    ],
                }
                result.append(synthetic)
            continue
        result.append(message)
        index += 1

    return result


is_completed_background_bash = isCompletedBackgroundBash
collapse_background_bash_notifications = collapseBackgroundBashNotifications


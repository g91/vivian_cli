"""
Port of src/utils/collapseTeammateShutdowns.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING


def isTeammateShutdownAttachment(msg):
    if not isinstance(msg, dict):
        return False
    attachment = msg.get('attachment') if isinstance(msg.get('attachment'), dict) else None
    return (
        msg.get('type') == 'attachment' and
        isinstance(attachment, dict) and
        attachment.get('type') == 'task_status' and
        attachment.get('taskType') == 'in_process_teammate' and
        attachment.get('status') == 'completed'
    )


def collapseTeammateShutdowns(messages):
    """Collapses consecutive in-process teammate shutdown task_status attachments
into a single `teammate_shutdown_batch` attachment with a count."""
    result = []
    index = 0
    messages = messages or []
    while index < len(messages):
        message = messages[index]
        if isTeammateShutdownAttachment(message):
            count = 0
            first = message
            while index < len(messages) and isTeammateShutdownAttachment(messages[index]):
                count += 1
                index += 1
            if count == 1:
                result.append(first)
            else:
                result.append({
                    'type': 'attachment',
                    'uuid': first.get('uuid'),
                    'timestamp': first.get('timestamp'),
                    'attachment': {
                        'type': 'teammate_shutdown_batch',
                        'count': count,
                    },
                })
            continue
        result.append(message)
        index += 1
    return result


is_teammate_shutdown_attachment = isTeammateShutdownAttachment
collapse_teammate_shutdowns = collapseTeammateShutdowns


"""
passpass of src/utils/unaryLogging.ts
"""
from __future__ import annotations

from typing import Any, Dict
import asyncio

from ..services.analytics.index import logEvent


CompletionType = Any
LogEvent = Dict[str, Any]


async def logUnaryEvent(event: LogEvent) -> None:
    metadata = event.get('metadata') or {}
    language_name = metadata.get('language_name')
    if asyncio.iscoroutine(language_name) or isinstance(language_name, asyncio.Future):
        language_name = await language_name
    logEvent(
        'tengu_unary_event',
        {
            'event': event.get('event'),
            'completion_type': event.get('completion_type'),
            'language_name': language_name,
            'message_id': metadata.get('message_id'),
            'platform': metadata.get('platform'),
            **({'hasFeedback': metadata.get('hasFeedback')} if metadata.get('hasFeedback') is not None else {}),
        },
    )


log_unary_event = logUnaryEvent

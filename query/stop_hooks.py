"""Stop-hook orchestration — mirrors src/query/stopHooks.ts.

Runs hooks registered for the 'stop', 'taskCompleted', and 'teammateIdle'
lifecycle events after the assistant produces its final response in a turn.
Yields stream events from hook scripts and returns a StopHookResult that
callers use to decide whether to re-enter the query loop.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Optional

log = logging.getLogger(__name__)


@dataclass
class StopHookResult:
    blockingErrors: list[dict] = field(default_factory=list)
    preventContinuation: bool = False


async def handleStopHooks(
    messagesForQuery: list[dict],
    assistantMessages: list[dict],
    systemPrompt: Any,
    userContext: Any,
    systemContext: Any,
    toolUseContext: Any,
    querySource: str,
    stopHookActive: Optional[bool] = None,
    _result_holder: Optional[list] = None,
) -> AsyncGenerator[Any, None]:
    """Execute stop hooks and yield stream events; return StopHookResult.

    This is an async generator. The caller iterates it to consume stream
    events from hook scripts. The return value (StopHookResult) is accessed
    via StopAsyncIteration.value when the generator is exhausted.

    Usage::

        gen = handleStopHooks(...)
        async for event in gen:
            handle_event(event)
        result: StopHookResult = gen.ag_return   # or via send/athrow pattern

    """
    result = StopHookResult()

    try:
        from vivian_cli.hooks.executor import executeStopHooks
    except ImportError:
        executeStopHooks = None

    try:
        from vivian_cli.hooks.task_hooks import (
            executeTaskCompletedHooks,
            executeTeammateIdleHooks,
        )
    except ImportError:
        executeTaskCompletedHooks = None
        executeTeammateIdleHooks = None

    try:
        from vivian_cli.hooks.summary import createStopHookSummaryMessage
    except ImportError:
        createStopHookSummaryMessage = None

    try:
        from vivian_cli.hooks.interruption import createUserInterruptionMessage
    except ImportError:
        createUserInterruptionMessage = None

    try:
        from vivian_cli.features import feature
    except ImportError:
        feature = lambda _: False  # noqa: E731

    try:
        from vivian_cli.coordinator.teammate import isTeammate
    except ImportError:
        isTeammate = lambda: False  # noqa: E731

    # Run primary stop hooks
    if executeStopHooks is not None and not stopHookActive:
        try:
            async for event in executeStopHooks(
                messagesForQuery,
                assistantMessages,
                systemPrompt,
                userContext,
                systemContext,
                toolUseContext,
                querySource,
            ):
                if isinstance(event, dict) and event.get("type") == "hook_error":
                    result.blockingErrors.append(event)
                    result.preventContinuation = True
                else:
                    yield event
        except Exception as exc:
            log.warning("stop hook error: %s", exc)
            result.blockingErrors.append({
                "type": "hook_error",
                "error": str(exc),
                "source": "stop",
            })

    # TeammateIdle + TaskCompleted hooks (teammate mode only)
    if isTeammate():
        if executeTeammateIdleHooks is not None:
            try:
                async for event in executeTeammateIdleHooks(
                    messagesForQuery, systemContext
                ):
                    yield event
            except Exception as exc:
                log.warning("teammate idle hook error: %s", exc)

        if executeTaskCompletedHooks is not None:
            try:
                async for event in executeTaskCompletedHooks(
                    messagesForQuery, systemContext
                ):
                    yield event
            except Exception as exc:
                log.warning("task completed hook error: %s", exc)

    # Yield summary message if hooks produced output
    if createStopHookSummaryMessage is not None and result.blockingErrors:
        summary = createStopHookSummaryMessage(result.blockingErrors)
        if summary:
            yield summary

    # NOTE: Python async generators cannot return values with a value.
    # Callers that need the StopHookResult should use collectStopHookResult(),
    # or pass _result_holder=[] and check holder[0] after iteration.
    if _result_holder is not None:
        _result_holder.append(result)
    return


async def collectStopHookResult(
    messagesForQuery: list[dict],
    assistantMessages: list[dict],
    systemPrompt: Any,
    userContext: Any,
    systemContext: Any,
    toolUseContext: Any,
    querySource: str,
    stopHookActive: Optional[bool] = None,
    event_callback: Any = None,
) -> StopHookResult:
    """Drive handleStopHooks to completion and return its StopHookResult.

    Calls event_callback(event) for each stream event produced by hooks.
    """
    result_holder: list = []
    gen = handleStopHooks(
        messagesForQuery,
        assistantMessages,
        systemPrompt,
        userContext,
        systemContext,
        toolUseContext,
        querySource,
        stopHookActive,
        _result_holder=result_holder,
    )
    try:
        async for event in gen:
            if event_callback:
                event_callback(event)
    except StopAsyncIteration:
        pass
    return result_holder[0] if result_holder else StopHookResult()

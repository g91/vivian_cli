"""Port of src/utils/telemetry/sessionTracing.ts."""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, TypedDict

from ..envUtils import is_env_defined_falsy, is_env_truthy
from .perfettoTracing import (
    endInteractionPerfettoSpan,
    endLLMRequestPerfettoSpan,
    endToolPerfettoSpan,
    endUserInputPerfettoSpan,
    isPerfettoTracingEnabled,
    startInteractionPerfettoSpan,
    startLLMRequestPerfettoSpan,
    startToolPerfettoSpan,
    startUserInputPerfettoSpan,
)


APIMessage = dict[str, Any]
SpanType = str


@dataclass
class _SpanId:
    spanId: str


@dataclass
class SimpleSpan:
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    ended: bool = False
    end_time_ms: float | None = None
    _span_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def spanContext(self):
        return _SpanId(self._span_id)

    def setAttributes(self, attrs: dict[str, Any]) -> None:
        self.attributes.update(attrs)

    def setAttribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def addEvent(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        self.events.append(
            {
                "name": name,
                "attributes": dict(attributes or {}),
                "timestamp": time.time() * 1000,
            }
        )

    def end(self) -> None:
        self.ended = True
        self.end_time_ms = time.time() * 1000


class SpanContext(TypedDict, total=False):
    span: SimpleSpan
    startTime: float
    attributes: dict[str, Any]
    ended: bool
    perfettoSpanId: str


interactionContext: ContextVar[SpanContext | None] = ContextVar("interactionContext", default=None)
toolContext: ContextVar[SpanContext | None] = ContextVar("toolContext", default=None)
activeSpans: dict[str, SpanContext] = {}
strongSpans: dict[str, SpanContext] = {}
interactionSequence = 0
_cleanupIntervalStarted = False
SPAN_TTL_MS = 30 * 60 * 1000


def getSpanId(span):
    return span.spanContext().spanId or ""


def _context_attrs(ctx: SpanContext | None) -> dict[str, Any]:
    return {} if not ctx else dict(ctx.get("attributes") or {})


def _set_context_var(context_var: ContextVar[SpanContext | None], value: SpanContext | None) -> None:
    context_var.set(value)


def _make_span_context(
    name: str,
    span_type: SpanType,
    attributes: dict[str, Any] | None = None,
    perfetto_span_id: str | None = None,
) -> SpanContext:
    span = SimpleSpan(name=name, attributes=createSpanAttributes(span_type, attributes or {}))
    return {
        "span": span,
        "startTime": time.time() * 1000,
        "attributes": dict(span.attributes),
        "ended": False,
        "perfettoSpanId": perfetto_span_id or "",
    }


def _store_span(span_context: SpanContext, *, keep_strong: bool = False) -> SimpleSpan:
    span = span_context["span"]
    span_id = getSpanId(span)
    activeSpans[span_id] = span_context
    if keep_strong:
        strongSpans[span_id] = span_context
    return span


def _remove_span(span: SimpleSpan) -> None:
    span_id = getSpanId(span)
    activeSpans.pop(span_id, None)
    strongSpans.pop(span_id, None)


def _end_span_context(span_context: SpanContext | None, extra_attrs: dict[str, Any] | None = None) -> None:
    if not span_context or span_context.get("ended"):
        return
    span = span_context["span"]
    duration = (time.time() * 1000) - span_context["startTime"]
    final_attrs = {"duration_ms": duration, **(extra_attrs or {})}
    span.setAttributes(final_attrs)
    span.end()
    span_context["ended"] = True
    _remove_span(span)


def ensureCleanupInterval():
    """Lazily mark cleanup enabled; stale spans are evicted opportunistically."""
    global _cleanupIntervalStarted
    _cleanupIntervalStarted = True


def _evict_stale_contexts() -> None:
    cutoff = (time.time() * 1000) - SPAN_TTL_MS
    for span_id, ctx in list(activeSpans.items()):
        if ctx["startTime"] < cutoff:
            if not ctx.get("ended"):
                ctx["span"].end()
                ctx["ended"] = True
            activeSpans.pop(span_id, None)
            strongSpans.pop(span_id, None)


def isEnhancedTelemetryEnabled():
    """Check if enhanced telemetry is enabled."""
    env = (
        os.environ.get("vivian_CODE_ENHANCED_TELEMETRY_BETA")
        or os.environ.get("ENABLE_ENHANCED_TELEMETRY_BETA")
    )
    if is_env_truthy(env):
        return True
    if is_env_defined_falsy(env):
        return False
    return os.environ.get("USER_TYPE") == "ant"


def isAnyTracingEnabled():
    """Check if any tracing is enabled."""
    return isEnhancedTelemetryEnabled() or isPerfettoTracingEnabled()


def getTracer():
    return "simple-tracer"


def createSpanAttributes(spanType, customAttributes=None):
    attributes = {"span.type": spanType}
    if customAttributes:
        attributes.update(customAttributes)
    return attributes


def startInteractionSpan(userPrompt):
    """Start an interaction span. This wraps a user request -> vivian response cycle."""
    global interactionSequence
    ensureCleanupInterval()
    _evict_stale_contexts()
    interactionSequence += 1

    perfetto_span_id = startInteractionPerfettoSpan(userPrompt) if isPerfettoTracingEnabled() else ""
    ctx = _make_span_context(
        "vivian_code.interaction",
        "interaction",
        {
            "user_prompt": userPrompt,
            "user_prompt_length": len(userPrompt or ""),
            "interaction.sequence": interactionSequence,
        },
        perfetto_span_id,
    )
    span = _store_span(ctx)
    _set_context_var(interactionContext, ctx)
    return span


def endInteractionSpan():
    span_context = interactionContext.get()
    if not span_context or span_context.get("ended"):
        return
    perfetto_span_id = span_context.get("perfettoSpanId")
    if perfetto_span_id:
        endInteractionPerfettoSpan(perfetto_span_id)
    _end_span_context(span_context, {"interaction.duration_ms": (time.time() * 1000) - span_context["startTime"]})
    _set_context_var(interactionContext, None)


def startLLMRequestSpan(model, newContext=None, messagesForAPI=None, fastMode=None):
    perfetto_span_id = ""
    if isPerfettoTracingEnabled():
        perfetto_span_id = startLLMRequestPerfettoSpan(
            {
                "model": model,
                "querySource": (newContext or {}).get("querySource") if isinstance(newContext, dict) else None,
            }
        )
    ctx = _make_span_context(
        "vivian_code.llm_request",
        "llm_request",
        {
            "model": model,
            "llm_request.context": "interaction" if interactionContext.get() else "standalone",
            "speed": "fast" if fastMode else "normal",
            "message_count": len(messagesForAPI or []),
        },
        perfetto_span_id,
    )
    return _store_span(ctx, keep_strong=True)


def endLLMRequestSpan(span=None, metadata=None):
    """End an LLM request span and attach response metadata."""
    metadata = metadata or {}
    if span is not None:
        llm_span_context = activeSpans.get(getSpanId(span))
    else:
        llm_span_context = next(
            (
                ctx
                for ctx in reversed(list(activeSpans.values()))
                if ctx["attributes"].get("span.type") == "llm_request"
            ),
            None,
        )
    if not llm_span_context:
        return

    perfetto_span_id = llm_span_context.get("perfettoSpanId")
    if perfetto_span_id:
        endLLMRequestPerfettoSpan(perfetto_span_id, metadata)

    _end_span_context(llm_span_context, dict(metadata))


def startToolSpan(toolName, toolAttributes=None, toolInput=None):
    perfetto_span_id = startToolPerfettoSpan(toolName, toolAttributes or {}) if isPerfettoTracingEnabled() else ""
    ctx = _make_span_context(
        "vivian_code.tool",
        "tool",
        {
            "tool_name": toolName,
            **(toolAttributes or {}),
            **({"tool_input": toolInput} if toolInput is not None and isToolContentLoggingEnabled() else {}),
        },
        perfetto_span_id,
    )
    span = _store_span(ctx)
    _set_context_var(toolContext, ctx)
    return span


def startToolBlockedOnUserSpan():
    ctx = _make_span_context("vivian_code.tool.blocked_on_user", "tool.blocked_on_user")
    return _store_span(ctx, keep_strong=True)


def endToolBlockedOnUserSpan(decision=None, source=None):
    blocked_ctx = next(
        (
            ctx
            for ctx in reversed(list(activeSpans.values()))
            if ctx["attributes"].get("span.type") == "tool.blocked_on_user"
        ),
        None,
    )
    _end_span_context(blocked_ctx, {"decision": decision, "source": source})


def startToolExecutionSpan():
    ctx = _make_span_context("vivian_code.tool.execution", "tool.execution")
    return _store_span(ctx, keep_strong=True)


def endToolExecutionSpan(metadata=None):
    exec_ctx = next(
        (
            ctx
            for ctx in reversed(list(activeSpans.values()))
            if ctx["attributes"].get("span.type") == "tool.execution"
        ),
        None,
    )
    _end_span_context(exec_ctx, dict(metadata or {}))


def endToolSpan(toolResult=None, resultTokens=None):
    span_context = toolContext.get()
    if not span_context or span_context.get("ended"):
        return
    perfetto_span_id = span_context.get("perfettoSpanId")
    if perfetto_span_id:
        endToolPerfettoSpan(perfetto_span_id, {"result_tokens": resultTokens})
    extra = {"result_tokens": resultTokens}
    if toolResult is not None and isToolContentLoggingEnabled():
        extra["tool_result"] = toolResult
    _end_span_context(span_context, extra)
    _set_context_var(toolContext, None)


def isToolContentLoggingEnabled():
    return is_env_truthy(os.environ.get("OTEL_LOG_TOOL_CONTENT", ""))


def addToolContentEvent(eventName, attributes):
    """Add a span event with tool content/output data."""
    span = getCurrentSpan()
    if span is None:
        return
    span.addEvent(eventName, dict(attributes or {}))


def getCurrentSpan():
    tool_ctx = toolContext.get()
    if tool_ctx and not tool_ctx.get("ended"):
        return tool_ctx["span"]
    interaction_ctx = interactionContext.get()
    if interaction_ctx and not interaction_ctx.get("ended"):
        return interaction_ctx["span"]
    return None


async def executeInSpan(spanName, string___number___boolean__, fn=None):
    span = SimpleSpan(
        name=str(spanName),
        attributes=createSpanAttributes("hook", dict(string___number___boolean__ or {})),
    )
    if fn is None:
        return span
    result = fn()
    if asyncio.iscoroutine(result):
        result = await result
    span.end()
    return result


def startHookSpan(hookEvent, hookName, numHooks, hookDefinitions):
    """Start a hook execution span."""
    ctx = _make_span_context(
        "vivian_code.hook",
        "hook",
        {
            "hook_event": hookEvent,
            "hook_name": hookName,
            "hook_count": numHooks,
            "hook_definitions": len(hookDefinitions or []),
        },
    )
    return _store_span(ctx, keep_strong=True)


def endHookSpan(span, metadata=None):
    """End a hook execution span with outcome metadata."""
    hook_ctx = activeSpans.get(getSpanId(span)) if span is not None else None
    _end_span_context(hook_ctx, dict(metadata or {}))


get_span_id = getSpanId
ensure_cleanup_interval = ensureCleanupInterval
is_enhanced_telemetry_enabled = isEnhancedTelemetryEnabled
is_any_tracing_enabled = isAnyTracingEnabled
get_tracer = getTracer
create_span_attributes = createSpanAttributes
start_interaction_span = startInteractionSpan
end_interaction_span = endInteractionSpan
start_llm_request_span = startLLMRequestSpan
end_llm_request_span = endLLMRequestSpan
start_tool_span = startToolSpan
start_tool_blocked_on_user_span = startToolBlockedOnUserSpan
end_tool_blocked_on_user_span = endToolBlockedOnUserSpan
start_tool_execution_span = startToolExecutionSpan
end_tool_execution_span = endToolExecutionSpan
end_tool_span = endToolSpan
is_tool_content_logging_enabled = isToolContentLoggingEnabled
add_tool_content_event = addToolContentEvent
get_current_span = getCurrentSpan
execute_in_span = executeInSpan
start_hook_span = startHookSpan
end_hook_span = endHookSpan


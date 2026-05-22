"""QueryEngine — owns the query lifecycle and session state.

Mirrors src/QueryEngine.ts and src/query.ts. One QueryEngine per conversation.
Each submit_message() call starts a new turn within the same conversation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional, AsyncGenerator, Union, Callable

from .api.client import VivianClient
from .bootstrap.state import getSessionId
from .types import (
    Message,
    QueryParams,
    QuerySource,
    ChatCompletionResponse,
    StreamChunk,
    Usage,
    AppState,
    CostState,
    TaskState,
    TaskStatus,
    TaskType,
    PermissionMode,
    ToolDefinition,
    CommandDefinition,
)
from .constants import (
    DEFAULT_MODEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    DEFAULT_MAX_TURNS,
    MAX_OUTPUT_TOKENS_RECOVERY_LIMIT,
    ERROR_IDS,
)
from .state.store import StateStore
from .cost_tracker import CostTracker
from .tools.registry import ToolRegistry
from .commands.registry import CommandRegistry
from .skills.registry import SkillRegistry
from .services.memory_service import MemoryService
from .services.compact_service import CompactService
from .services.vivianAiLimits import (
    extractQuotaStatusFromHeaders,
    extractQuotaStatusFromError,
    checkQuotaStatus,
)
from .services.rateLimitMessages import isRateLimitErrorMessage
from .services.tokenEstimation import (
    roughTokenCountEstimationForMessages,
)
from .services.SessionMemory import (
    getSessionMemoryContent,
    hasMetInitializationThreshold,
    hasMetUpdateThreshold,
    markSessionMemoryInitialized,
    markExtractionStarted,
    markExtractionCompleted,
    recordExtractionTokenCount,
    isSessionMemoryInitialized,
)
from .services.tools import executeToolBatch
from .services.toolUseSummary import generateToolUseSummary
from .services.mcp import mcpInfoFromString, buildMcpToolName
from .utils.commitAttribution import incrementPromptCount
from .utils.fileHistory import fileHistoryMakeSnapshot
from .utils.sessionStorage import recordAttributionSnapshot, recordTranscript
from .utils.context import build_system_prompt, get_git_status
from .utils.debug_log import dlog as _dlog, dlog_exc as _dlog_exc
from .utils.format import format_duration
from .utils.toolResultStorage import (
    DEFAULT_MAX_RESULT_SIZE_CHARS,
    processPreMappedToolResultBlock,
)
from .query.config import buildQueryConfig, QueryConfig
from .query.token_budget import createBudgetTracker, checkTokenBudget, ContinueDecision, BudgetTracker
from .query.stop_hooks import collectStopHookResult
from .query.deps import productionDeps, QueryDeps

logger = logging.getLogger(__name__)

# Tools whose result includes the full resulting file content — strip it before
# adding to conversation history. The model only needs success/failure + metadata.
_FILE_MODIFY_TOOLS = frozenset({
    "Edit", "edit", "file_edit", "edit_file", "patch_file", "replace_in_file",
    "Write", "write", "file_write", "write_file", "create_file",
    "Move", "move", "rename_file",
    "Delete", "delete", "remove_file",
    "NotebookEdit", "notebook_edit",
})
# Maximum characters kept in any single string value in a tool result message.
_TOOL_RESULT_MAX_STR = 6000


def _sanitize_tool_result_for_history(tool_name: str, result: Any) -> Any:
    """Return a trimmed copy of *result* safe to embed in conversation history.

    - For file-modification tools: removes the 'content' field (full file body).
    - For all results: truncates any string value longer than _TOOL_RESULT_MAX_STR.
    """
    if not isinstance(result, dict):
        v = str(result)
        return v[:_TOOL_RESULT_MAX_STR] + "…" if len(v) > _TOOL_RESULT_MAX_STR else v
    r = dict(result)
    if tool_name in _FILE_MODIFY_TOOLS:
        r.pop("content", None)
    for k, v in list(r.items()):
        if isinstance(v, str) and len(v) > _TOOL_RESULT_MAX_STR:
            r[k] = v[:_TOOL_RESULT_MAX_STR] + f"… [{len(v) - _TOOL_RESULT_MAX_STR} chars truncated]"
    return r


def _iso_utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _text_content_blocks(content: Optional[str]) -> list[dict[str, Any]]:
    return [{"type": "text", "text": content or ""}]


def _assistant_content_blocks(message: Message) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    if message.content:
        blocks.append({"type": "text", "text": message.content})
    if message.tool_calls:
        for tool_call in message.tool_calls:
            function = tool_call.get("function") or {}
            try:
                tool_input = json.loads(function.get("arguments") or "{}")
            except json.JSONDecodeError:
                tool_input = {}
            blocks.append(
                {
                    "type": "tool_use",
                    "id": tool_call.get("id"),
                    "name": function.get("name"),
                    "input": tool_input,
                }
            )
    return blocks


def _tool_result_content_blocks(tool_call_id: str, content: Optional[str]) -> list[dict[str, Any]]:
    parsed_content: Any = content or ""
    if isinstance(parsed_content, str):
        try:
            parsed_content = json.loads(parsed_content)
        except json.JSONDecodeError:
            pass
    return [{"type": "tool_result", "tool_use_id": tool_call_id, "content": parsed_content}]


async def _format_tool_result_message_content(tool_name: str, tool_call_id: str, result: Any) -> str:
    raw_content = json.dumps(result) if isinstance(result, dict) else str(result)
    processed_block = await processPreMappedToolResultBlock(
        {
            "type": "tool_result",
            "tool_use_id": tool_call_id,
            "content": raw_content,
        },
        tool_name,
        DEFAULT_MAX_RESULT_SIZE_CHARS,
    )
    if isinstance(processed_block, dict) and processed_block.get("content") is not None:
        return str(processed_block["content"])
    return raw_content


class QueryEngine:
    """Manages the full query lifecycle for a Vivian conversation.

    One QueryEngine per conversation. State (messages, cost, usage, etc.)
    persists across turns.
    """

    def __init__(
        self,
        client: VivianClient,
        *,
        tools: Optional[list[ToolDefinition]] = None,
        tool_registry: Optional[ToolRegistry] = None,
        commands: Optional[list[CommandDefinition]] = None,
        initial_messages: Optional[list[Message]] = None,
        custom_system_prompt: Optional[str] = None,
        append_system_prompt: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_turns: int = DEFAULT_MAX_TURNS,
        max_budget_usd: Optional[float] = None,
        permission_mode: PermissionMode = PermissionMode.DEFAULT,
        username: Optional[str] = None,
        cwd: str = ".",
        coordinator_mode: bool = False,
    ):
        self.client = client
        self.model = model
        self.max_turns = max_turns
        self.max_budget_usd = max_budget_usd
        self.permission_mode = permission_mode
        self.username = username
        self.cwd = str(Path(cwd).resolve()) if cwd and cwd != "." else os.getcwd()
        self.coordinator_mode = coordinator_mode

        # State
        self.messages: list[Message] = initial_messages or []
        self.state_store = StateStore()
        self.cost_tracker = CostTracker()
        # Prefer a pre-built registry (which has handlers) over a bare list of definitions.
        if tool_registry is not None:
            self.tool_registry = tool_registry
        else:
            self.tool_registry = ToolRegistry(tools or [])
        self.command_registry = CommandRegistry(commands or [])
        self.skill_registry = SkillRegistry()
        self.memory_service = MemoryService(client)
        self.compact_service = CompactService()

        # Rate-limit & token services (available to tools and response handlers)
        self._last_response_headers: dict = {}
        self._current_token_count: int = 0

        # System prompt
        self.custom_system_prompt = custom_system_prompt
        self.append_system_prompt = append_system_prompt

        # Turn tracking
        self.turn_count = 0
        self.session_id = str(getSessionId())
        self._last_transcript_uuid: Optional[str] = None
        self._current_turn_user_uuid: Optional[str] = None
        self._abort = asyncio.Event()
        self._discovered_skill_names: set[str] = set()

        # Query configuration gates & deps (from query/ modules)
        self._query_config: QueryConfig = buildQueryConfig()
        self._budget_tracker: BudgetTracker = createBudgetTracker()
        self._query_deps: QueryDeps = productionDeps()

        # Recovery
        self._max_output_tokens_recovery_count = 0
        self._has_attempted_reactive_compact = False

    @property
    def app_state(self) -> AppState:
        return self.state_store.get_state()

    def interrupt(self):
        """Interrupt the current query."""
        self._abort.set()

    def reset_interrupt(self):
        self._abort.clear()

    async def submit_message(
        self,
        prompt: Union[str, list[dict[str, Any]]],
        *,
        is_meta: bool = False,
        query_source: QuerySource = QuerySource.REPL_MAIN,
    ) -> AsyncGenerator[Union[Message, StreamChunk, dict[str, Any]], None]:
        """Submit a user message and yield the conversation stream.

        Yields Message objects, StreamChunks, and tool-call events.
        """
        self.reset_interrupt()
        self.turn_count += 1
        self._discovered_skill_names.clear()

        user_transcript_uuid = str(uuid.uuid4())

        # Build user message
        if isinstance(prompt, str):
            user_msg = Message(role="user", content=prompt)
        else:
            # Content blocks
            user_msg = Message(role="user", content=json.dumps(prompt))

        self.messages.append(user_msg)
        self._current_turn_user_uuid = user_transcript_uuid
        self._last_transcript_uuid = recordTranscript(
            [
                {
                    "type": "user",
                    "role": "user",
                    "uuid": user_transcript_uuid,
                    "message": {
                        "role": "user",
                        "content": _text_content_blocks(user_msg.content),
                    },
                    "content": _text_content_blocks(user_msg.content),
                    "timestamp": _iso_utc_now(),
                }
            ],
            startingParentUuid=self._last_transcript_uuid,
        )
        await fileHistoryMakeSnapshot(
            lambda updater: self.state_store.set_state(
                lambda prev: {
                    **prev,
                    "fileHistory": updater(prev.get("fileHistory")),
                }
            ),
            user_transcript_uuid,
        )
        self.state_store.set_state(
            lambda prev: {
                **prev,
                "attribution": incrementPromptCount(prev.get("attribution"), recordAttributionSnapshot),
            }
        )

        # Build system prompt
        system_prompt = await self._build_system_prompt()

        # Get tools
        available_tools = self.tool_registry.get_enabled_tools()
        tool_defs = [t.to_openai_schema() for t in available_tools] if available_tools else None

        # Main query loop
        params = QueryParams(
            messages=list(self.messages),
            system_prompt=system_prompt,
            user_context={"cwd": self.cwd},
            system_context={},
            model=self.model,
            max_tokens=DEFAULT_MAX_TOKENS,
            temperature=DEFAULT_TEMPERATURE,
            top_p=DEFAULT_TOP_P,
            stream=True,
            tools=tool_defs,
            tool_choice="auto",
            max_turns=self.max_turns,
            query_source=query_source,
            username=self.username,
        )

        async for event in self._query_loop(params):
            if self._abort.is_set():
                yield Message(role="system", content="[Interrupted by user]")
                break
            yield event

    async def _build_system_prompt(self) -> str:
        """Build the full system prompt with context."""
        parts = []

        # Load output styles from cwd (async, cached internally)
        output_styles: list[dict] = []
        try:
            from .output_styles import getOutputStyleDirStyles
            output_styles = await getOutputStyleDirStyles(self.cwd)
        except Exception:
            pass

        if self.custom_system_prompt:
            parts.append(self.custom_system_prompt)
        else:
            parts.append(await build_system_prompt(
                tools=self.tool_registry.get_enabled_tools(),
                commands=self.command_registry.get_enabled_commands(),
                skills=self.skill_registry.get_enabled_skills(),
                model=self.model,
                cwd=self.cwd,
                output_styles=output_styles if output_styles else None,
            ))

        # Git status
        git_status = await get_git_status(self.cwd)
        if git_status:
            parts.append(git_status)

        if self.append_system_prompt:
            parts.append(self.append_system_prompt)

        # Coordinator mode context
        if self.coordinator_mode:
            from .coordinator.coordinatorMode import getCoordinatorUserContext
            ctx = getCoordinatorUserContext()
            if ctx.get("coordinatorContext"):
                parts.append(ctx["coordinatorContext"])

        return "\n\n".join(parts)

    async def _query_loop(
        self, params: QueryParams
    ) -> AsyncGenerator[Union[Message, StreamChunk, dict[str, Any]], None]:
        """Main query loop — handles tool calls, compaction, recovery."""
        def _dbg(m: str) -> None:
            _dlog("query: %s", m)
        messages = list(params.messages)
        _dbg(f"_query_loop START history_len={len(messages)} cwd={os.getcwd()} max_turns={params.max_turns}")
        # Pick up any cwd change (e.g. from a previous `cd`) made via os.chdir().
        self.cwd = os.getcwd()
        tool_use_context = {
            "query_source": params.query_source.value,
            "turn_count": self.turn_count,
            "cwd": self.cwd,
            "registry": self.tool_registry,
            "file_history_message_id": self._current_turn_user_uuid,
            "update_file_history_state": lambda updater: self.state_store.set_state(
                lambda prev: {
                    **prev,
                    "fileHistory": updater(prev.get("fileHistory")),
                }
            ),
            "attribution_message_id": self._current_turn_user_uuid,
            "update_attribution_state": lambda updater: self.state_store.set_state(
                lambda prev: {
                    **prev,
                    "attribution": updater(prev.get("attribution")),
                }
            ),
        }
        # Per-turn global token count (approximate; updated after each API call)
        global_turn_tokens: int = 0

        for turn in range(params.max_turns):
            _dbg(f"  turn {turn} starting, abort={self._abort.is_set()}, msgs={len(messages)}")
            if self._abort.is_set():
                _dbg(f"  → abort set, breaking")
                break

            # ── Token budget gate ──────────────────────────────────────────
            if self._query_config.gates.fastModeEnabled:
                budget_decision = checkTokenBudget(
                    self._budget_tracker,
                    self.session_id,
                    params.max_tokens,
                    global_turn_tokens,
                )
                if not isinstance(budget_decision, ContinueDecision):
                    yield Message(
                        role="system",
                        content=f"[Token budget limit reached — {type(budget_decision).__name__}]",
                    )
                    break

            # Check USD budget
            if self.max_budget_usd and self.cost_tracker.total_cost_usd >= self.max_budget_usd:
                yield Message(
                    role="system",
                    content=f"Budget limit of ${self.max_budget_usd:.2f} reached.",
                )
                break

            # Auto-compact if needed
            if self.compact_service.should_compact(messages):
                messages = await self.compact_service.compact(
                    messages, self.client, self.model
                )
                yield Message(role="system", content="[Context compacted]")

            # Make API call
            try:
                import time as _time
                _api_start = _time.monotonic()
                response = await self.client.chat_completions(
                    messages=messages,
                    model=params.model,
                    stream=True,
                    temperature=params.temperature,
                    max_tokens=params.max_tokens,
                    top_p=params.top_p,
                    tools=params.tools,
                    tool_choice=params.tool_choice,
                    username=params.username,
                )

                # Collect assistant response
                assistant_content = ""
                assistant_tool_calls: list[dict[str, Any]] = []
                finish_reason = None
                _usage_from_api: dict = {}   # populated if the API sends usage in final chunk

                # Track which tool slots have already emitted a start event
                _announced_tool_slots: set[int] = set()

                async for chunk in response:
                    if self._abort.is_set():
                        break

                    yield chunk

                    # Capture usage from final chunk (requires stream_options.include_usage=true)
                    if hasattr(chunk, "usage") and chunk.usage:
                        _usage_from_api = chunk.usage if isinstance(chunk.usage, dict) else {}

                    # Extract response headers if available (for rate limit tracking)
                    if hasattr(chunk, "_headers"):
                        try:
                            extractQuotaStatusFromHeaders(chunk._headers)
                            self._last_response_headers = dict(chunk._headers)
                        except Exception:
                            pass

                    for choice in chunk.choices:
                        delta = choice.get("delta", {})
                        if delta.get("content"):
                            assistant_content += delta["content"]
                        if delta.get("tool_calls"):
                            for tc in delta["tool_calls"]:
                                idx = tc.get("index", 0)
                                while len(assistant_tool_calls) <= idx:
                                    assistant_tool_calls.append({
                                        "id": "",
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""},
                                    })
                                if tc.get("id"):
                                    assistant_tool_calls[idx]["id"] = tc["id"]
                                if tc.get("function", {}).get("name"):
                                    new_name = tc["function"]["name"]
                                    assistant_tool_calls[idx]["function"]["name"] = new_name
                                    # Emit live tool_call_start as soon as we know the name
                                    if idx not in _announced_tool_slots and new_name:
                                        _announced_tool_slots.add(idx)
                                        yield {"type": "tool_call_start", "name": new_name, "index": idx}
                                if tc.get("function", {}).get("arguments"):
                                    assistant_tool_calls[idx]["function"]["arguments"] += tc["function"]["arguments"]
                        finish_reason = choice.get("finish_reason") or finish_reason

                # Build assistant message
                # Mark it as already_streamed so the UI doesn't re-print text
                # that was already displayed token-by-token via stream chunks.
                assistant_msg = Message(role="assistant")
                if assistant_content:
                    assistant_msg.content = assistant_content
                if assistant_tool_calls:
                    assistant_msg.tool_calls = assistant_tool_calls
                assistant_msg.already_streamed = True  # type: ignore[attr-defined]

                _dbg(f"    stream done: finish={finish_reason!r} content_len={len(assistant_content)} tool_calls={len(assistant_tool_calls)}")
                if assistant_tool_calls:
                    for tc in assistant_tool_calls:
                        _dbg(f"      tool_call: name={tc['function']['name']!r} args={tc['function']['arguments'][:200]!r}")

                # Only append assistant message if it has actual content or tool calls.
                # An empty message (e.g. from a garbled/empty stream response) would
                # accumulate in history and confuse the model on subsequent turns.
                _has_content = bool(assistant_content or assistant_tool_calls)
                if _has_content:
                    messages.append(assistant_msg)
                    self.messages.append(assistant_msg)
                    self._last_transcript_uuid = recordTranscript(
                        [
                            {
                                "type": "assistant",
                                "role": "assistant",
                                "uuid": str(uuid.uuid4()),
                                "message": {
                                    "role": "assistant",
                                    "content": _assistant_content_blocks(assistant_msg),
                                },
                                "content": _assistant_content_blocks(assistant_msg),
                                "timestamp": _iso_utc_now(),
                            }
                        ],
                        startingParentUuid=self._last_transcript_uuid,
                    )
                else:
                    _dlog("query: skipping empty assistant message (finish=%r)", finish_reason)

                # Track cost + API duration
                _api_ms = (_time.monotonic() - _api_start) * 1000
                # Prefer real token counts from the API's usage field
                if _usage_from_api:
                    input_tok  = _usage_from_api.get("prompt_tokens", 0) or _usage_from_api.get("input_tokens", 0)
                    output_tok = _usage_from_api.get("completion_tokens", 0) or _usage_from_api.get("output_tokens", 0)
                else:
                    # Fallback: rough character-based estimate
                    input_tok  = sum(len(str(m)) for m in messages) // 4
                    output_tok = len(assistant_content) // 4
                self.cost_tracker.add_usage(
                    input_tokens=input_tok,
                    output_tokens=output_tok,
                    model=params.model or self.model or "unknown",
                    api_duration_ms=_api_ms,
                )
                global_turn_tokens += input_tok + output_tok
                self._current_token_count = global_turn_tokens

                # Session memory: check thresholds and extract if needed
                if not isSessionMemoryInitialized() and hasMetInitializationThreshold(global_turn_tokens):
                    markSessionMemoryInitialized()
                elif isSessionMemoryInitialized() and hasMetUpdateThreshold(global_turn_tokens):
                    # Trigger background session memory extraction
                    try:
                        markExtractionStarted()
                        recordExtractionTokenCount(global_turn_tokens)
                        # Actual extraction happens via extractMemories (wired in cli_main)
                        markExtractionCompleted()
                    except Exception:
                        markExtractionCompleted()

                # Handle tool calls.
                # Some models (e.g. Qwen) return finish_reason="stop" even when
                # tool_calls are present in the delta, so we check for tool calls
                # first regardless of finish_reason.
                if assistant_tool_calls:
                    # Some providers stream tool_calls without an `id`. Without a
                    # stable id the next-turn payload pairs the tool result with
                    # an empty assistant tool_call id — the API treats the tool
                    # message as orphan and returns an empty completion, locking
                    # the conversation. Ensure every entry has the SAME id on
                    # both the assistant tool_calls list and the tool reply.
                    for i, tc in enumerate(assistant_tool_calls):
                        if not tc.get("id"):
                            tc["id"] = f"call_{tc['function']['name']}_{turn}_{i}_{uuid.uuid4().hex[:8]}"
                            _dbg(f"      synthesized tool_call id for slot {i}: {tc['id']}")

                    completed_tools = []
                    for tc in assistant_tool_calls:
                        if self._abort.is_set():
                            break

                        tool_name = tc["function"]["name"]
                        try:
                            tool_args = json.loads(tc["function"]["arguments"])
                        except json.JSONDecodeError:
                            tool_args = {}

                        # Emit args event so the UI can show what's being called
                        yield {"type": "tool_call_args", "name": tool_name, "args": tool_args}

                        # Execute tool
                        _dbg(f"      executing tool: {tool_name!r} args={str(tool_args)[:200]}")
                        try:
                            tool_result = await self.tool_registry.execute_tool(
                                tool_name, tool_args, context=tool_use_context
                            )
                        except Exception as _tool_exc:
                            _dlog_exc(f"tool execute RAISED {tool_name!r}", _tool_exc)
                            tool_result = {"error": f"{type(_tool_exc).__name__}: {_tool_exc}"}
                        _dbg(f"      tool result: {str(tool_result)[:300]}")

                        # Track lines changed for file edit/write tools
                        if isinstance(tool_result, dict) and not tool_result.get("error"):
                            la = tool_result.get("linesAdded") or 0
                            lr = tool_result.get("linesRemoved") or 0
                            if la or lr:
                                self.cost_tracker.add_lines_changed(added=la, removed=lr)

                        # Add tool result message — id MUST equal the assistant
                        # message's tool_calls[i].id (set above) for the model to
                        # see this as the reply to that call.
                        #
                        # Sanitise before encoding: strip large file-content blobs
                        # from edit/write results (the model doesn't need to re-read
                        # the whole file) and truncate any remaining oversized strings.
                        # Oversized content in the JSON body causes the Ollama proxy
                        # to fail with "Value looks like object, but can't find '}'"
                        _history_result = _sanitize_tool_result_for_history(tool_name, tool_result)
                        _mcp_meta = None
                        if isinstance(tool_result, dict):
                            meta = tool_result.get("_meta")
                            structured = tool_result.get("structuredContent")
                            if isinstance(meta, dict) or isinstance(structured, dict):
                                _mcp_meta = {}
                                if isinstance(meta, dict):
                                    _mcp_meta["_meta"] = meta
                                if isinstance(structured, dict):
                                    _mcp_meta["structuredContent"] = structured
                        result_msg = Message(
                            role="tool",
                            tool_call_id=tc["id"],
                            content=await _format_tool_result_message_content(
                                tool_name,
                                tc["id"],
                                _history_result,
                            ),
                        )
                        messages.append(result_msg)
                        self.messages.append(result_msg)
                        self._last_transcript_uuid = recordTranscript(
                            [
                                {
                                    "type": "user",
                                    "role": "user",
                                    "uuid": str(uuid.uuid4()),
                                    "toolUseResult": _history_result,
                                    **({"mcpMeta": _mcp_meta} if _mcp_meta else {}),
                                    "message": {
                                        "role": "user",
                                        "content": _tool_result_content_blocks(tc["id"], result_msg.content),
                                    },
                                    "content": _tool_result_content_blocks(tc["id"], result_msg.content),
                                    "timestamp": _iso_utc_now(),
                                }
                            ],
                            startingParentUuid=self._last_transcript_uuid,
                        )

                        yield {
                            "type": "tool_result",
                            "tool_call_id": tc["id"],
                            "tool_name": tool_name,
                            "result": tool_result,
                            **({"mcpMeta": _mcp_meta} if _mcp_meta else {}),
                            "args": tool_args,
                        }

                        completed_tools.append({
                            "name": tool_name,
                            "input": tool_args,
                            "output": tool_result,
                        })

                    # Generate tool use summary (non-blocking, best-effort)
                    if completed_tools:
                        try:
                            summary = await generateToolUseSummary(
                                tools=completed_tools,
                                last_assistant_text=assistant_content[:200] if assistant_content else None,
                            )
                            if summary:
                                yield {"type": "tool_use_summary", "summary": summary}
                        except Exception:
                            pass

                    continue  # Continue loop for next assistant response

                elif finish_reason in ("stop", None):
                    # Natural completion — run stop hooks then decide whether to
                    # re-enter the loop (e.g. blocking hooks that need another turn)
                    if not _has_content:
                        # Model returned an empty response — break silently rather
                        # than yielding an empty message and confusing the UI.
                        _dlog("query: empty response — breaking turn loop")
                        break
                    yield assistant_msg
                    stop_result = await collectStopHookResult(
                        list(messages),
                        [assistant_msg.__dict__ if hasattr(assistant_msg, "__dict__") else {"role": "assistant", "content": assistant_content}],
                        params.system_prompt if hasattr(params, "system_prompt") else None,
                        tool_use_context,
                        tool_use_context,
                        tool_use_context,
                        params.query_source.value if hasattr(params.query_source, "value") else str(params.query_source),
                    )
                    if stop_result.preventContinuation or not stop_result.blockingErrors:
                        break
                    # Hooks produced blocking errors — feed them back as a user turn
                    error_summary = "\n".join(str(e) for e in stop_result.blockingErrors)
                    messages.append(Message(role="user", content=f"[Hook errors]\n{error_summary}"))
                    continue

                elif finish_reason == "length":
                    # Max tokens reached — try recovery
                    self._max_output_tokens_recovery_count += 1
                    if self._max_output_tokens_recovery_count <= MAX_OUTPUT_TOKENS_RECOVERY_LIMIT:
                        yield Message(
                            role="system",
                            content="[Continuing — output was truncated]",
                        )
                        continue
                    else:
                        yield Message(
                            role="system",
                            content="[Max output tokens limit reached]",
                        )
                        break

                else:
                    yield assistant_msg
                    break

            except Exception as e:
                # Check if this is a rate limit error and emit friendly message
                err_str = str(e)
                if isRateLimitErrorMessage(err_str):
                    try:
                        extractQuotaStatusFromError({"message": err_str})
                    except Exception:
                        pass
                logger.error(f"Query error: {e}")
                yield Message(role="system", content=f"Error: {e}")
                break

    def get_messages(self) -> list[Message]:
        return list(self.messages)

    def get_session_id(self) -> str:
        return self.session_id

    def set_model(self, model: str):
        self.model = model

    def get_cost_summary(self) -> str:
        return self.cost_tracker.format_total_cost()


async def ask(
    client: VivianClient,
    prompt: str,
    *,
    tools: Optional[list[ToolDefinition]] = None,
    commands: Optional[list[CommandDefinition]] = None,
    model: str = DEFAULT_MODEL,
    max_turns: int = DEFAULT_MAX_TURNS,
    max_budget_usd: Optional[float] = None,
    custom_system_prompt: Optional[str] = None,
    username: Optional[str] = None,
    cwd: str = ".",
) -> AsyncGenerator[Union[Message, StreamChunk, dict[str, Any]], None]:
    """Convenience wrapper for one-shot queries.

    Usage:
        async for event in ask(client, "Write a hello world program"):
            print(event)
    """
    engine = QueryEngine(
        client,
        tools=tools,
        commands=commands,
        model=model,
        max_turns=max_turns,
        max_budget_usd=max_budget_usd,
        custom_system_prompt=custom_system_prompt,
        username=username,
        cwd=cwd,
    )

    async for event in engine.submit_message(prompt):
        yield event

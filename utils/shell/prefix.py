"""Port of src/utils/shell/prefix.ts."""
from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Awaitable, Callable, Dict, Optional, TypedDict

from ...services.analytics.growthbook import getFeatureValue_CACHED_MAY_BE_STALE
from ...services.analytics.index import logEvent
from ...services.api.vivian import queryModelWithoutStreaming
from ..memoize import memoizeWithLRU
from ..slowOperations import jsonStringify
from ..systemPromptType import asSystemPrompt


DANGEROUS_SHELL_PREFIXES = {
    "sh",
    "bash",
    "zsh",
    "fish",
    "csh",
    "tcsh",
    "ksh",
    "dash",
    "cmd",
    "cmd.exe",
    "powershell",
    "powershell.exe",
    "pwsh",
    "pwsh.exe",
    "bash.exe",
}


class CommandPrefixResult(TypedDict):
    commandPrefix: str | None


class CommandSubcommandPrefixResult(CommandPrefixResult):
    subcommandPrefixes: dict[str, CommandPrefixResult]


PrefixExtractorConfig = Dict[str, Any]


def _extract_response_text(response: dict[str, Any]) -> str:
    content = response.get("message", {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return str(block.get("text", ""))
            if hasattr(block, "text"):
                return str(getattr(block, "text"))
    return str(response.get("text", ""))


def _looks_like_api_error(prefix: str, response: dict[str, Any]) -> bool:
    if response.get("isApiErrorMessage"):
        return True
    normalized = prefix.strip().lower()
    return normalized.startswith("api error") or normalized.startswith("error:")


def createCommandPrefixExtractor(config: PrefixExtractorConfig):
    """Creates a memoized command prefix extractor function."""
    tool_name = config["toolName"]
    policy_spec = config["policySpec"]
    event_name = config["eventName"]
    query_source = config["querySource"]
    pre_check = config.get("preCheck")

    def _factory(command: str, abort_signal: Any, is_non_interactive_session: bool):
        task = asyncio.create_task(
            getCommandPrefixImpl(
                command,
                abort_signal,
                is_non_interactive_session,
                tool_name,
                policy_spec,
                event_name,
                query_source,
                pre_check,
            )
        )

        def _evict_on_error(done: asyncio.Task):
            if done.cancelled():
                if memoized.cache.get(command) is task:
                    memoized.cache.delete(command)
                return
            error = done.exception()
            if error is not None and memoized.cache.get(command) is task:
                memoized.cache.delete(command)

        task.add_done_callback(_evict_on_error)
        return task

    memoized = memoizeWithLRU(_factory, lambda command, *_args: command, 200)

    async def _wrapper(command: str, abort_signal: Any, is_non_interactive_session: bool):
        return await memoized(command, abort_signal, is_non_interactive_session)

    _wrapper.cache = memoized.cache  # type: ignore[attr-defined]
    return _wrapper


def createSubcommandPrefixExtractor(
    getPrefix: Callable[[str, Any, bool], Awaitable[Optional[CommandPrefixResult]]],
    splitCommand: Callable[[str], list[str] | Awaitable[list[str]]],
):
    """Creates a memoized function to get prefixes for compound commands with subcommands."""

    def _factory(command: str, abort_signal: Any, is_non_interactive_session: bool):
        task = asyncio.create_task(
            getCommandSubcommandPrefixImpl(
                command,
                abort_signal,
                is_non_interactive_session,
                getPrefix,
                splitCommand,
            )
        )

        def _evict_on_error(done: asyncio.Task):
            if done.cancelled():
                if memoized.cache.get(command) is task:
                    memoized.cache.delete(command)
                return
            error = done.exception()
            if error is not None and memoized.cache.get(command) is task:
                memoized.cache.delete(command)

        task.add_done_callback(_evict_on_error)
        return task

    memoized = memoizeWithLRU(_factory, lambda command, *_args: command, 200)

    async def _wrapper(command: str, abort_signal: Any, is_non_interactive_session: bool):
        return await memoized(command, abort_signal, is_non_interactive_session)

    _wrapper.cache = memoized.cache  # type: ignore[attr-defined]
    return _wrapper


async def getCommandPrefixImpl(
    command: str,
    abortSignal: Any,
    isNonInteractiveSession: bool,
    toolName: str,
    policySpec: str,
    eventName: str,
    querySource: str,
    preCheck: Optional[Callable[[str], Optional[CommandPrefixResult]]] = None,
) -> Optional[CommandPrefixResult]:
    if os.environ.get("NODE_ENV") == "test":
        return None

    if preCheck:
        pre_check_result = preCheck(command)
        if pre_check_result is not None:
            return pre_check_result

    timeout_task: asyncio.Task | None = None
    start_time = asyncio.get_running_loop().time()
    try:
        async def _warn_late() -> None:
            await asyncio.sleep(10)
            message = (
                f"[{toolName}Tool] Pre-flight check is taking longer than expected. "
                "Run with ANTHROPIC_LOG=debug to check for failed or slow API requests."
            )
            if isNonInteractiveSession:
                sys.stderr.write(jsonStringify({"level": "warn", "message": message}) + "\n")
            else:
                print(message, file=sys.stderr)

        timeout_task = asyncio.create_task(_warn_late())
        use_system_prompt_policy_spec = bool(
            getFeatureValue_CACHED_MAY_BE_STALE("tengu_cork_m4q", False)
        )

        response = await queryModelWithoutStreaming(
            {
                "messages": [{"role": "user", "content": f"Command: {command}" if use_system_prompt_policy_spec else f"{policySpec}\n\nCommand: {command}"}],
                "systemPrompt": [
                    {
                        "type": "text",
                        "text": asSystemPrompt(
                            [
                                (
                                    f"Your task is to process {toolName} commands that an AI coding agent wants to run.\n\n{policySpec}"
                                    if use_system_prompt_policy_spec
                                    else (
                                        f"Your task is to process {toolName} commands that an AI coding agent wants to run.\n\n"
                                        f"This policy spec defines how to determine the prefix of a {toolName} command:"
                                    )
                                )
                            ]
                        )[0],
                    }
                ],
                "signal": abortSignal,
                "options": {
                    "enablePromptCaching": use_system_prompt_policy_spec,
                    "querySource": querySource,
                    "agents": [],
                    "isNonInteractiveSession": isNonInteractiveSession,
                    "hasAppendSystemPrompt": False,
                    "mcpTools": [],
                },
            }
        )

        if timeout_task:
            timeout_task.cancel()
        duration_ms = int((asyncio.get_running_loop().time() - start_time) * 1000)
        prefix = _extract_response_text(response).strip() or "none"

        if _looks_like_api_error(prefix, response):
            logEvent(eventName, {"success": False, "error": "API error", "durationMs": duration_ms})
            return None
        if prefix == "command_injection_detected":
            logEvent(eventName, {"success": False, "error": "command_injection_detected", "durationMs": duration_ms})
            return {"commandPrefix": None}
        if prefix == "git" or prefix.lower() in DANGEROUS_SHELL_PREFIXES:
            logEvent(eventName, {"success": False, "error": "dangerous_shell_prefix", "durationMs": duration_ms})
            return {"commandPrefix": None}
        if prefix == "none":
            logEvent(eventName, {"success": False, "error": 'prefix "none"', "durationMs": duration_ms})
            return {"commandPrefix": None}
        if not command.startswith(prefix):
            logEvent(eventName, {"success": False, "error": "command did not start with prefix", "durationMs": duration_ms})
            return {"commandPrefix": None}

        logEvent(eventName, {"success": True, "durationMs": duration_ms})
        return {"commandPrefix": prefix}
    finally:
        if timeout_task:
            timeout_task.cancel()


async def getCommandSubcommandPrefixImpl(
    command: str,
    abortSignal: Any,
    isNonInteractiveSession: bool,
    getPrefix: Callable[[str, Any, bool], Awaitable[Optional[CommandPrefixResult]]],
    splitCommandFn: Callable[[str], list[str] | Awaitable[list[str]]],
) -> Optional[CommandSubcommandPrefixResult]:
    subcommands_or_awaitable = splitCommandFn(command)
    subcommands = (
        await subcommands_or_awaitable
        if asyncio.iscoroutine(subcommands_or_awaitable)
        else subcommands_or_awaitable
    )

    full_command_prefix, *subcommand_prefix_results = await asyncio.gather(
        getPrefix(command, abortSignal, isNonInteractiveSession),
        *[
            _get_subcommand_prefix(subcommand, abortSignal, isNonInteractiveSession, getPrefix)
            for subcommand in subcommands
        ],
    )
    if not full_command_prefix:
        return None

    subcommand_prefixes: dict[str, CommandPrefixResult] = {}
    for entry in subcommand_prefix_results:
        subcommand = entry["subcommand"]
        prefix = entry["prefix"]
        if prefix:
            subcommand_prefixes[subcommand] = prefix

    return {
        **full_command_prefix,
        "subcommandPrefixes": subcommand_prefixes,
    }


async def _get_subcommand_prefix(
    subcommand: str,
    abort_signal: Any,
    is_non_interactive_session: bool,
    get_prefix: Callable[[str, Any, bool], Awaitable[Optional[CommandPrefixResult]]],
) -> dict[str, Any]:
    return {
        "subcommand": subcommand,
        "prefix": await get_prefix(subcommand, abort_signal, is_non_interactive_session),
    }


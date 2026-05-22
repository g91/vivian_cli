"""Port of src/utils/processUserInput/processSlashCommand.tsx."""
from __future__ import annotations

import asyncio
import inspect
import os
import re
from typing import Any

from ...commands import findCommand, getCommands, getSlashCommandToolSkills
from ...types.command import CompactResult, SkipResult, TextResult, getCommandName
from ..messages import createUserMessage


SlashCommandResult = dict[str, Any]
_VALID_COMMAND_RE = re.compile(r"^[A-Za-z0-9:_-]+$")


def _system_message(text: str) -> dict[str, Any]:
    return {"type": "system", "text": text}


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def executeForkedSlashCommand(command, args, context, precedingInputBlocks, setToolJSX, canUseTool):
    del precedingInputBlocks, setToolJSX, canUseTool
    return await getMessagesForPromptSlashCommand(command, args, context)


def looksLikeCommand(commandName):
    return bool(_VALID_COMMAND_RE.fullmatch(commandName or ""))


async def processSlashCommand(inputString, precedingInputBlocks, imageContentBlocks, attachmentMessages, context, setToolJSX, uuid=None, isAlreadyProcessing=None, canUseTool=None):
    del attachmentMessages
    stripped = (inputString or "").strip()
    body = stripped[1:] if stripped.startswith("/") else stripped
    if not body:
        return {"messages": [_system_message("Missing slash command")], "shouldQuery": False}
    command_name, _, args = body.partition(" ")
    if not looksLikeCommand(command_name):
        return {"messages": [_system_message(f"Invalid command name: {command_name}")], "shouldQuery": False}
    return await getMessagesForSlashCommand(
        command_name,
        args.strip(),
        setToolJSX,
        context,
        precedingInputBlocks,
        imageContentBlocks,
        isAlreadyProcessing,
        canUseTool,
        uuid,
    )


async def getMessagesForSlashCommand(commandName, args, setToolJSX, context, precedingInputBlocks, imageContentBlocks, _isAlreadyProcessing=None, canUseTool=None, uuid=None):
    del setToolJSX, canUseTool, precedingInputBlocks, _isAlreadyProcessing
    cwd = getattr(context, "cwd", None) or os.getcwd()
    commands = [*(await getCommands(cwd)), *(await getSlashCommandToolSkills(cwd))]
    command = findCommand(commandName, commands)
    if command is None:
        return {"messages": [_system_message(f"Unknown command: /{commandName}")], "shouldQuery": False}

    command_type = getattr(command, "type", None)
    if command_type == "prompt":
        return await processPromptSlashCommand(commandName, args, commands, context, imageContentBlocks=imageContentBlocks)

    if command_type == "local":
        module_or_command = await _maybe_await(getattr(command, "load", lambda: command)())
        call = getattr(module_or_command, "call", None) or getattr(command, "call", None)
        if not callable(call):
            return {"messages": [_system_message(f"Command /{commandName} is not callable")], "shouldQuery": False}
        result = await _maybe_await(call(args, context))
        return _normalize_local_command_result(result)

    if command_type == "local-jsx":
        module_or_command = await _maybe_await(getattr(command, "load", lambda: command)())
        call = getattr(module_or_command, "call", None) or getattr(command, "call", None)
        if not callable(call):
            return {"messages": [_system_message(f"Command /{commandName} is not callable")], "shouldQuery": False}
        holder: dict[str, Any] = {}

        def on_done(result: str | None = None, options: dict[str, Any] | None = None) -> None:
            holder["result"] = result
            holder["options"] = options or {}

        await _maybe_await(call(on_done, context, args))
        result_text = holder.get("result") or ""
        return {
            "messages": [_system_message(result_text)] if result_text else [],
            "shouldQuery": False,
            "resultText": result_text or None,
            **(holder.get("options") or {}),
        }

    return {"messages": [_system_message(f"Unsupported command type for /{commandName}")], "shouldQuery": False}


def _normalize_local_command_result(result: Any) -> SlashCommandResult:
    if isinstance(result, TextResult):
        return {"messages": [_system_message(result.value)], "shouldQuery": False, "resultText": result.value}
    if isinstance(result, CompactResult):
        text = result.displayText or ""
        return {"messages": [_system_message(text)] if text else [], "shouldQuery": False, "resultText": text or None}
    if isinstance(result, SkipResult):
        return {"messages": [], "shouldQuery": False}
    if isinstance(result, str):
        return {"messages": [_system_message(result)], "shouldQuery": False, "resultText": result}
    if isinstance(result, dict):
        return {"messages": [result], "shouldQuery": False}
    return {"messages": [_system_message(str(result))], "shouldQuery": False, "resultText": str(result)}


def formatCommandInput(command, args):
    command_name = getCommandName(command)
    return f"/{command_name}{(' ' + args) if args else ''}"


def formatSkillLoadingMetadata(skillName, _progressMessage='loading'):
    return f"The {skillName} skill is running"


def formatSlashCommandLoadingMetadata(commandName, args=None):
    return f"/{commandName}{(' ' + args) if args else ''}"


def formatCommandLoadingMetadata(command, args=None):
    if getattr(command, "userInvocable", True):
        return formatSlashCommandLoadingMetadata(getattr(command, "name", ""), args)
    return formatSkillLoadingMetadata(getattr(command, "name", ""), getattr(command, "progressMessage", "loading"))


async def processPromptSlashCommand(commandName, args, commands, context, imageContentBlocks=[]):
    command = findCommand(commandName, commands)
    if command is None:
        return {"messages": [_system_message(f"Unknown command: /{commandName}")], "shouldQuery": False}
    return await getMessagesForPromptSlashCommand(command, args, context, imageContentBlocks=imageContentBlocks)


async def getMessagesForPromptSlashCommand(command, args, context, precedingInputBlocks=[], imageContentBlocks=[], uuid=None):
    del precedingInputBlocks
    prompt_builder = getattr(command, "getPromptForCommand", None)
    if callable(prompt_builder):
        prompt = await _maybe_await(prompt_builder(args, context))
    else:
        prompt = formatCommandInput(command, args)

    content = prompt
    if imageContentBlocks:
        if isinstance(prompt, list):
            content = [*prompt, *imageContentBlocks]
        else:
            blocks = []
            if isinstance(prompt, str) and prompt:
                blocks.append({"type": "text", "text": prompt})
            content = [*blocks, *imageContentBlocks]

    user_message = createUserMessage({"content": content, "uuid": uuid})
    return {
        "messages": [user_message],
        "shouldQuery": True,
        "allowedTools": getattr(command, "allowedTools", None),
        "model": getattr(command, "model", None),
        "effort": getattr(command, "effort", None),
    }


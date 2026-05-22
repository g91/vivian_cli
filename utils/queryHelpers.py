"""Port of src/utils/queryHelpers.ts."""
from __future__ import annotations

from typing import Any
import re

from ..constants.tools import (
    BASH_TOOL_NAME,
    FILE_EDIT_TOOL_NAME,
    FILE_READ_TOOL_NAME,
    FILE_WRITE_TOOL_NAME,
)
from ..tools.FileReadTool.prompt import FILE_UNCHANGED_STUB
from .file import getFileModificationTime, stripLineNumberPrefix
from .fileRead import readFileSyncWithMetadata
from .fileStateCache import createFileStateCacheWithSizeLimit
from .path import expandPath


PermissionPromptTool = Any
ASK_READ_FILE_STATE_CACHE_SIZE = 10
_SYSTEM_REMINDER_RE = re.compile(r"<system-reminder>[\s\S]*?</system-reminder>")
_ENV_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_]\w*=")
_STRIPPED_COMMANDS = {"sudo"}


def isResultSuccessful(message, stopReason=None):
    """Checks if the result should be considered successful based on the last message."""
    if not message:
        return False

    message_type = message.get("type") if isinstance(message, dict) else getattr(message, "type", None)
    if message_type == "assistant":
        assistant_message = message.get("message", {}) if isinstance(message, dict) else getattr(message, "message", {})
        content = assistant_message.get("content") if isinstance(assistant_message, dict) else getattr(assistant_message, "content", None)
        if isinstance(content, list) and content:
            last_content = content[-1]
            if isinstance(last_content, dict) and last_content.get("type") in {"text", "thinking", "redacted_thinking"}:
                return True

    if message_type == "user":
        user_message = message.get("message", {}) if isinstance(message, dict) else getattr(message, "message", {})
        content = user_message.get("content") if isinstance(user_message, dict) else getattr(user_message, "content", None)
        if isinstance(content, list) and content and all(
            isinstance(block, dict) and block.get("type") == "tool_result"
            for block in content
        ):
            return True

    return stopReason == "end_turn"


def extractReadFilesFromMessages(messages, cwd, maxSize=ASK_READ_FILE_STATE_CACHE_SIZE):
    cache = createFileStateCacheWithSizeLimit(maxSize)

    file_read_tool_use_ids: dict[str, str] = {}
    file_write_tool_use_ids: dict[str, dict[str, str]] = {}
    file_edit_tool_use_ids: dict[str, str] = {}

    for message in messages or []:
        if not isinstance(message, dict) or message.get("type") != "assistant":
            continue
        content_list = message.get("message", {}).get("content")
        if not isinstance(content_list, list):
            continue

        for content in content_list:
            if not isinstance(content, dict) or content.get("type") != "tool_use":
                continue

            tool_name = content.get("name")
            tool_input = content.get("input") or {}
            tool_use_id = content.get("id")
            if not tool_use_id or not isinstance(tool_input, dict):
                continue

            if tool_name == FILE_READ_TOOL_NAME:
                file_path = tool_input.get("file_path")
                if file_path and tool_input.get("offset") is None and tool_input.get("limit") is None:
                    file_read_tool_use_ids[str(tool_use_id)] = expandPath(file_path, cwd)
            elif tool_name == FILE_WRITE_TOOL_NAME:
                file_path = tool_input.get("file_path")
                file_content = tool_input.get("content")
                if file_path and file_content is not None:
                    file_write_tool_use_ids[str(tool_use_id)] = {
                        "filePath": expandPath(file_path, cwd),
                        "content": str(file_content),
                    }
            elif tool_name == FILE_EDIT_TOOL_NAME:
                file_path = tool_input.get("file_path")
                if file_path:
                    file_edit_tool_use_ids[str(tool_use_id)] = expandPath(file_path, cwd)

    for message in messages or []:
        if not isinstance(message, dict) or message.get("type") != "user":
            continue
        content_list = message.get("message", {}).get("content")
        if not isinstance(content_list, list):
            continue

        timestamp_value = message.get("timestamp")
        try:
            timestamp_ms = int(timestamp_value) if isinstance(timestamp_value, (int, float)) else None
        except Exception:
            timestamp_ms = None

        for content in content_list:
            if not isinstance(content, dict) or content.get("type") != "tool_result":
                continue
            tool_use_id = content.get("tool_use_id")
            if not tool_use_id:
                continue

            read_file_path = file_read_tool_use_ids.get(str(tool_use_id))
            if (
                read_file_path
                and isinstance(content.get("content"), str)
                and not content["content"].startswith(FILE_UNCHANGED_STUB)
                and timestamp_ms is not None
            ):
                processed = _SYSTEM_REMINDER_RE.sub("", content["content"])
                file_content = "\n".join(
                    stripLineNumberPrefix(line) for line in processed.split("\n")
                ).strip()
                cache.set(
                    read_file_path,
                    {
                        "content": file_content,
                        "timestamp": timestamp_ms,
                        "offset": None,
                        "limit": None,
                    },
                )

            write_tool_data = file_write_tool_use_ids.get(str(tool_use_id))
            if write_tool_data and timestamp_ms is not None:
                cache.set(
                    write_tool_data["filePath"],
                    {
                        "content": write_tool_data["content"],
                        "timestamp": timestamp_ms,
                        "offset": None,
                        "limit": None,
                    },
                )

            edit_file_path = file_edit_tool_use_ids.get(str(tool_use_id))
            if edit_file_path and content.get("is_error") is not True:
                try:
                    disk_content = readFileSyncWithMetadata(edit_file_path).content
                    cache.set(
                        edit_file_path,
                        {
                            "content": disk_content,
                            "timestamp": getFileModificationTime(edit_file_path),
                            "offset": None,
                            "limit": None,
                        },
                    )
                except OSError:
                    pass

    return cache


def extractBashToolsFromMessages(messages):
    """Extract the top-level CLI tools used in BashTool calls from message history."""
    tools: set[str] = set()
    for message in messages or []:
        if not isinstance(message, dict) or message.get("type") != "assistant":
            continue
        content_list = message.get("message", {}).get("content")
        if not isinstance(content_list, list):
            continue

        for content in content_list:
            if (
                isinstance(content, dict)
                and content.get("type") == "tool_use"
                and content.get("name") == BASH_TOOL_NAME
            ):
                tool_input = content.get("input")
                if not isinstance(tool_input, dict):
                    continue
                cli_name = extractCliName(tool_input.get("command"))
                if cli_name:
                    tools.add(cli_name)
    return tools


def extractCliName(command):
    """Extract the actual CLI name from a bash command string, skipping"""
    if not isinstance(command, str) or not command.strip():
        return None
    for token in command.strip().split():
        if _ENV_ASSIGNMENT_RE.match(token):
            continue
        if token in _STRIPPED_COMMANDS:
            continue
        return token
    return None


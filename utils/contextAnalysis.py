"""
passpasspasspass of src/utils/contextAnalysis
"""
from __future__ import annotations

from typing import Any
import json
from collections.abc import Iterable

from ..services.tokenEstimation import roughTokenCountEstimation as countTokens
from .slowOperations import jsonStringify


TokenStats = dict[str, Any]


def _new_stats() -> TokenStats:
    return {
        "toolRequests": {},
        "toolResults": {},
        "humanMessages": 0,
        "assistantMessages": 0,
        "localCommandOutputs": 0,
        "other": 0,
        "attachments": {},
        "duplicateFileReads": {},
        "total": 0,
    }


def _normalize_messages_for_api(messages: Iterable[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        msg_type = message.get("type")
        if msg_type not in {"user", "assistant"}:
            continue

        nested = message.get("message") if isinstance(message.get("message"), dict) else {}
        content = nested.get("content")
        if content is None:
            content = message.get("content")
        if content is None:
            content = []

        normalized.append(
            {
                "type": msg_type,
                "message": {
                    "role": nested.get("role") or message.get("role") or msg_type,
                    "content": content,
                },
            }
        )
    return normalized


def analyzeContext(messages):
    stats = _new_stats()
    tool_ids_to_tool_names: dict[str, str] = {}
    read_tool_id_to_file_path: dict[str, str] = {}
    file_read_stats: dict[str, dict[str, int]] = {}

    for msg in messages or []:
        if not isinstance(msg, dict) or msg.get("type") != "attachment":
            continue
        attachment = msg.get("attachment") or {}
        attachment_type = attachment.get("type") or "unknown"
        increment(stats["attachments"], str(attachment_type), 1)

    normalized_messages = _normalize_messages_for_api(messages or [])
    for msg in normalized_messages:
        content = msg["message"].get("content")
        if isinstance(content, str):
            tokens = countTokens(content)
            stats["total"] += tokens
            if msg.get("type") == "user" and "local-command-stdout" in content:
                stats["localCommandOutputs"] += tokens
            elif msg.get("type") == "user":
                stats["humanMessages"] += tokens
            else:
                stats["assistantMessages"] += tokens
            continue

        if isinstance(content, list):
            for block in content:
                processBlock(
                    block,
                    msg,
                    stats,
                    tool_ids_to_tool_names,
                    read_tool_id_to_file_path,
                    file_read_stats,
                )

    for path, data in file_read_stats.items():
        if data["count"] > 1:
            average_tokens_per_read = data["totalTokens"] // data["count"]
            duplicate_tokens = average_tokens_per_read * (data["count"] - 1)
            stats["duplicateFileReads"][path] = {
                "count": data["count"],
                "tokens": duplicate_tokens,
            }

    return stats


def processBlock(block, message, stats, toolIds, readToolPaths, fileReads):
    if not isinstance(block, dict):
        return None

    tokens = countTokens(jsonStringify(block))
    stats["total"] += tokens
    block_type = block.get("type")

    if block_type == "text":
        block_text = block.get("text", "")
        if message.get("type") == "user" and isinstance(block_text, str) and "local-command-stdout" in block_text:
            stats["localCommandOutputs"] += tokens
        elif message.get("type") == "user":
            stats["humanMessages"] += tokens
        else:
            stats["assistantMessages"] += tokens
        return None

    if block_type == "tool_use":
        tool_name = str(block.get("name") or "unknown")
        tool_id = block.get("id")
        increment(stats["toolRequests"], tool_name, tokens)
        if isinstance(tool_id, str):
            toolIds[tool_id] = tool_name
            tool_input = block.get("input")
            if tool_name == "Read" and isinstance(tool_input, dict) and "file_path" in tool_input:
                readToolPaths[tool_id] = str(tool_input.get("file_path"))
        return None

    if block_type == "tool_result":
        tool_use_id = block.get("tool_use_id")
        if isinstance(tool_use_id, str):
            tool_name = toolIds.get(tool_use_id, "unknown")
            increment(stats["toolResults"], tool_name, tokens)
            if tool_name == "Read":
                path = readToolPaths.get(tool_use_id)
                if path:
                    current = fileReads.get(path, {"count": 0, "totalTokens": 0})
                    fileReads[path] = {
                        "count": current["count"] + 1,
                        "totalTokens": current["totalTokens"] + tokens,
                    }
        return None

    if block_type in {
        "image",
        "server_tool_use",
        "web_search_tool_result",
        "search_result",
        "document",
        "thinking",
        "redacted_thinking",
        "code_execution_tool_result",
        "mcp_tool_use",
        "mcp_tool_result",
        "container_upload",
        "web_fetch_tool_result",
        "bash_code_execution_tool_result",
        "text_editor_code_execution_tool_result",
        "tool_search_tool_result",
        "compaction",
    }:
        stats["other"] += tokens
    return None


def increment(map, key, value):
    map[key] = (map.get(key) or 0) + value


def tokenStatsToStatsigMetrics(stats):
    metrics: dict[str, int] = {
        "total_tokens": stats["total"],
        "human_message_tokens": stats["humanMessages"],
        "assistant_message_tokens": stats["assistantMessages"],
        "local_command_output_tokens": stats["localCommandOutputs"],
        "other_tokens": stats["other"],
    }

    for attachment_type, count in stats["attachments"].items():
        metrics[f"attachment_{attachment_type}_count"] = count

    for tool, tokens in stats["toolRequests"].items():
        metrics[f"tool_request_{tool}_tokens"] = tokens

    for tool, tokens in stats["toolResults"].items():
        metrics[f"tool_result_{tool}_tokens"] = tokens

    duplicate_total = sum(item["tokens"] for item in stats["duplicateFileReads"].values())
    metrics["duplicate_read_tokens"] = duplicate_total
    metrics["duplicate_read_file_count"] = len(stats["duplicateFileReads"])

    if stats["total"] > 0:
        metrics["human_message_percent"] = round((stats["humanMessages"] / stats["total"]) * 100)
        metrics["assistant_message_percent"] = round((stats["assistantMessages"] / stats["total"]) * 100)
        metrics["local_command_output_percent"] = round((stats["localCommandOutputs"] / stats["total"]) * 100)
        metrics["duplicate_read_percent"] = round((duplicate_total / stats["total"]) * 100)

        tool_request_total = sum(stats["toolRequests"].values())
        tool_result_total = sum(stats["toolResults"].values())
        metrics["tool_request_percent"] = round((tool_request_total / stats["total"]) * 100)
        metrics["tool_result_percent"] = round((tool_result_total / stats["total"]) * 100)

        for tool, tokens in stats["toolRequests"].items():
            metrics[f"tool_request_{tool}_percent"] = round((tokens / stats["total"]) * 100)
        for tool, tokens in stats["toolResults"].items():
            metrics[f"tool_result_{tool}_percent"] = round((tokens / stats["total"]) * 100)

    return metrics


analyze_context = analyzeContext
process_block = processBlock
token_stats_to_statsig_metrics = tokenStatsToStatsigMetrics


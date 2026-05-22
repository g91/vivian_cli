"""MCPTool — mirrors src/tools/MCPTool/MCPTool.tsx"""
from __future__ import annotations
import inspect
import os
import time
from typing import Any, Dict

from ...services.mcp import normalizeNameForMCP
from ...services.analytics import logEvent
from ...utils.codeIndexing import detectCodeIndexingFromMcpServerName
from ...utils.envUtils import is_env_defined_falsy
from ...utils.mcpOutputStorage import getFormatDescription, getLargeOutputInstructions
from ...utils.mcpValidation import getContentSizeEstimate, mcpContentNeedsTruncation, truncateMcpContent, truncateMcpContentIfNeeded
from ...utils.toolResultStorage import hasImageBlock, persistToolResult

TOOL_NAME_PREFIX = "mcp__"

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "server": {"type": "string"},
        "tool": {"type": "string"},
        "arguments": {"type": "object"},
    },
}


async def description() -> str:
    return "Call a tool on a connected MCP server."


async def prompt() -> str:
    return "Use this tool to call tools exposed by connected MCP servers."


def _client_value(client: Any, key: str, default: Any = None) -> Any:
    if isinstance(client, dict):
        return client.get(key, default)
    return getattr(client, key, default)


def _get_mcp_clients(context: Any) -> list[Any]:
    if isinstance(context, dict):
        if isinstance(context.get("mcpClients"), list):
            return context["mcpClients"]
        options = context.get("options")
        if isinstance(options, dict) and isinstance(options.get("mcpClients"), list):
            return options["mcpClients"]
    return []


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _call_mcp_tool(client: Any, tool_name: str, arguments: Dict[str, Any]) -> Any:
    direct_client = _client_value(client, "client")
    call_tool = getattr(direct_client, "call_tool", None) if direct_client is not None else None
    if call_tool is None:
        call_tool = getattr(client, "call_tool", None)
    if callable(call_tool):
        return await _maybe_await(call_tool(tool_name, arguments))

    request = getattr(direct_client, "request", None) if direct_client is not None else None
    if request is None:
        request = getattr(client, "request", None)
    if callable(request):
        return await _maybe_await(
            request({"method": "tools/call", "params": {"name": tool_name, "arguments": arguments}})
        )

    raise RuntimeError("MCP client does not support tool calls")


def _extract_mcp_error_details(result: Dict[str, Any]) -> str:
    content = result.get("content")
    if isinstance(content, list) and content:
        first_content = content[0]
        if isinstance(first_content, dict) and isinstance(first_content.get("text"), str):
            return first_content["text"]
    if "error" in result:
        return str(result.get("error"))
    return "Unknown error"


async def _process_mcp_content(result: Dict[str, Any], tool_name: str, server_name: str) -> Any:
    if "content" not in result:
        return result

    content = result["content"]
    if server_name == "ide":
        return content

    if not (await mcpContentNeedsTruncation(content)):
        return content

    size_estimate_tokens = getContentSizeEstimate(content)
    if is_env_defined_falsy(os.environ.get("ENABLE_MCP_LARGE_OUTPUT_FILES")):
        logEvent(
            "tengu_mcp_large_result_handled",
            {
                "outcome": "truncated",
                "reason": "env_disabled",
                "sizeEstimateTokens": size_estimate_tokens,
            },
        )
        return await truncateMcpContent(content)

    if hasImageBlock(content):
        logEvent(
            "tengu_mcp_large_result_handled",
            {
                "outcome": "truncated",
                "reason": "contains_images",
                "sizeEstimateTokens": size_estimate_tokens,
            },
        )
        return await truncateMcpContent(content)

    persist_id = f"mcp-{normalizeNameForMCP(server_name)}-{normalizeNameForMCP(tool_name)}-{int(time.time() * 1000)}"
    persist_result = await persistToolResult(content, persist_id)
    if isinstance(persist_result, dict) and "error" in persist_result:
        content_length = len(content) if isinstance(content, str) else len(str(content))
        logEvent(
            "tengu_mcp_large_result_handled",
            {
                "outcome": "truncated",
                "reason": "persist_failed",
                "sizeEstimateTokens": size_estimate_tokens,
            },
        )
        return (
            f"Error: result ({content_length:,} characters) exceeds maximum allowed tokens. "
            f"Failed to save output to file: {persist_result['error']}. "
            "If this MCP server provides pagination or filtering tools, use them to retrieve specific portions of the data."
        )

    logEvent(
        "tengu_mcp_large_result_handled",
        {
            "outcome": "persisted",
            "reason": "file_saved",
            "sizeEstimateTokens": size_estimate_tokens,
            "persistedSizeChars": persist_result["originalSize"],
        },
    )
    format_description = getFormatDescription("toolResult" if isinstance(content, str) else "contentArray")
    return getLargeOutputInstructions(
        persist_result["filepath"],
        persist_result["originalSize"],
        format_description,
    )


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    server_name = input_data.get("server")
    tool_name = input_data.get("tool")
    arguments = input_data.get("arguments") or {}
    mcp_clients = _get_mcp_clients(context)

    if not server_name:
        return {"error": "server is required"}
    if not tool_name:
        return {"error": "tool is required"}

    client = next((item for item in mcp_clients if _client_value(item, "name") == server_name), None)
    if client is None:
        available = ", ".join(str(_client_value(item, "name", "")) for item in mcp_clients if _client_value(item, "name"))
        return {"error": f'Server "{server_name}" not found. Available servers: {available}'}
    if _client_value(client, "type") != "connected":
        return {"error": f'Server "{server_name}" is not connected'}

    try:
        result = await _call_mcp_tool(client, str(tool_name), dict(arguments))
    except Exception as exc:
        return {"error": str(exc)}

    if isinstance(result, dict) and result.get("isError"):
        error_details = _extract_mcp_error_details(result)
        error_result: Dict[str, Any] = {"error": error_details}
        if isinstance(result.get("_meta"), dict):
            error_result["_meta"] = result["_meta"]
        return error_result

    code_indexing_tool = detectCodeIndexingFromMcpServerName(str(server_name))
    if code_indexing_tool:
        logEvent(
            "tengu_code_indexing_tool_used",
            {
                "tool": code_indexing_tool,
                "source": "mcp",
                "success": True,
            },
        )

    if isinstance(result, dict):
        output: Dict[str, Any] = {}
        if "content" in result:
            processed_content = await _process_mcp_content(result, str(tool_name), str(server_name))
            output["result"] = processed_content
            output["content"] = processed_content
        else:
            output["result"] = result

        if isinstance(result.get("_meta"), dict):
            output["_meta"] = result["_meta"]
        if isinstance(result.get("structuredContent"), dict):
            output["structuredContent"] = result["structuredContent"]
        return output

    return {"result": result}

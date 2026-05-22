"""Port of src/utils/mcpValidation.ts."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
import os


MCPToolResult = Optional[Union[str, List[Dict[str, Any]]]]


MCP_TOKEN_COUNT_THRESHOLD_FACTOR: Any = 0.5  # type: ignore
IMAGE_TOKEN_ESTIMATE: Any = 1600  # type: ignore
DEFAULT_MAX_MCP_OUTPUT_TOKENS = 25000


def getMaxMcpOutputTokens():
    """Resolve the MCP output token cap. Precedence:"""
    env_value = os.environ.get("MAX_MCP_OUTPUT_TOKENS")
    if env_value:
        try:
            parsed = int(env_value, 10)
        except ValueError:
            parsed = 0
        if parsed > 0:
            return parsed

    try:
        from ..services.analytics.growthbook import getFeatureValue_CACHED_MAY_BE_STALE

        overrides = getFeatureValue_CACHED_MAY_BE_STALE("tengu_satin_quoll", {})
        override = overrides.get("mcp_tool") if isinstance(overrides, dict) else None
        if isinstance(override, (int, float)) and override > 0:
            return int(override)
    except Exception:
        pass

    return DEFAULT_MAX_MCP_OUTPUT_TOKENS


def isTextBlock(block):
    return isinstance(block, dict) and block.get("type") == "text"


def isImageBlock(block):
    return isinstance(block, dict) and block.get("type") == "image"


def getContentSizeEstimate(content):
    if not content:
        return 0
    if isinstance(content, str):
        from ..services.tokenEstimation import roughTokenCountEstimation

        return roughTokenCountEstimation(content)

    from ..services.tokenEstimation import roughTokenCountEstimation

    total = 0
    for block in content:
        if isTextBlock(block):
            total += roughTokenCountEstimation(block.get("text", ""))
        elif isImageBlock(block):
            total += IMAGE_TOKEN_ESTIMATE
    return total


def getMaxMcpOutputChars():
    return getMaxMcpOutputTokens() * 4


def getTruncationMessage():
    return (
        f"\n\n[OUTPUT TRUNCATED - exceeded {getMaxMcpOutputTokens()} token limit]\n\n"
        "The tool output was truncated. If this MCP server provides pagination or filtering tools, "
        "use them to retrieve specific portions of the data. If pagination is not available, inform "
        "the user that you are working with truncated output and results may be incomplete."
    )


def truncateString(content, maxChars):
    if len(content) <= maxChars:
        return content
    return content[:maxChars]


async def truncateContentBlocks(blocks, maxChars):
    result: List[Dict[str, Any]] = []
    current_chars = 0

    for block in blocks:
        if isTextBlock(block):
            remaining_chars = maxChars - current_chars
            if remaining_chars <= 0:
                break
            text = block.get("text", "")
            if len(text) <= remaining_chars:
                result.append(block)
                current_chars += len(text)
            else:
                result.append({"type": "text", "text": text[:remaining_chars]})
                break
        elif isImageBlock(block):
            image_chars = IMAGE_TOKEN_ESTIMATE * 4
            if current_chars + image_chars <= maxChars:
                result.append(block)
                current_chars += image_chars
            else:
                remaining_chars = maxChars - current_chars
                if remaining_chars > 0:
                    remaining_bytes = int(remaining_chars * 0.75)
                    try:
                        from .imageResizer import compressImageBlock

                        compressed_block = await compressImageBlock(block, remaining_bytes)
                        result.append(compressed_block)
                        source = compressed_block.get("source", {}) if isinstance(compressed_block, dict) else {}
                        if source.get("type") == "base64":
                            current_chars += len(source.get("data", ""))
                        else:
                            current_chars += image_chars
                    except Exception:
                        pass
        else:
            result.append(block)
    return result


async def mcpContentNeedsTruncation(content):
    if not content:
        return False

    content_size_estimate = getContentSizeEstimate(content)
    if content_size_estimate <= getMaxMcpOutputTokens() * MCP_TOKEN_COUNT_THRESHOLD_FACTOR:
        return False

    try:
        from ..services.tokenEstimation import countMessagesTokensWithAPI

        messages = [{"role": "user", "content": content}]
        token_count = await countMessagesTokensWithAPI(messages, [])
        return bool(token_count and token_count > getMaxMcpOutputTokens())
    except Exception as error:
        try:
            from .debug import log_error

            log_error("MCP token counting failed", error if isinstance(error, Exception) else None)
        except Exception:
            pass
        return False


async def truncateMcpContent(content):
    if not content:
        return content

    max_chars = getMaxMcpOutputChars()
    truncation_msg = getTruncationMessage()
    if isinstance(content, str):
        return truncateString(content, max_chars) + truncation_msg

    truncated_blocks = await truncateContentBlocks(content, max_chars)
    truncated_blocks.append({"type": "text", "text": truncation_msg})
    return truncated_blocks


async def truncateMcpContentIfNeeded(content):
    if not (await mcpContentNeedsTruncation(content)):
        return content
    return await truncateMcpContent(content)


get_max_mcp_output_tokens = getMaxMcpOutputTokens
get_content_size_estimate = getContentSizeEstimate
get_truncation_message = getTruncationMessage
truncate_string = truncateString
truncate_content_blocks = truncateContentBlocks
mcp_content_needs_truncation = mcpContentNeedsTruncation
truncate_mcp_content = truncateMcpContent
truncate_mcp_content_if_needed = truncateMcpContentIfNeeded


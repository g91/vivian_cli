"""Content array helpers — mirrors src/utils/contentArray.ts"""
from __future__ import annotations


def insert_block_after_tool_results(content: list, block: object) -> None:
    """Insert block after the last tool_result block in content (in place).

    If no tool_result blocks exist, inserts before the last block.
    If the inserted block would be the final element, appends a text
    continuation block so the prompt doesn't end with non-text content.
    """
    last_tool_result_idx = -1
    for i, item in enumerate(content):
        if isinstance(item, dict) and item.get("type") == "tool_result":
            last_tool_result_idx = i

    if last_tool_result_idx >= 0:
        insert_pos = last_tool_result_idx + 1
        content.insert(insert_pos, block)
        if insert_pos == len(content) - 1:
            content.append({"type": "text", "text": "."})
    else:
        insert_index = max(0, len(content) - 1)
        content.insert(insert_index, block)

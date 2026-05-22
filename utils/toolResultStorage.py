"""Tool result persistence helpers mirroring src/utils/toolResultStorage.ts."""

from __future__ import annotations

import asyncio
import math
from pathlib import Path
from typing import Any, Optional

from ..bootstrap.state import getOriginalCwd, getSessionId
from ..services.analytics.growthbook import getFeatureValue_CACHED_MAY_BE_STALE
from ..services.analytics.index import logEvent
from .debug import logForDebugging
from .log import logError
from .sessionStorage import getProjectDir
from .slowOperations import jsonStringify

PersistedToolResult = dict[str, Any]
PersistToolResultError = dict[str, Any]
ContentReplacementState = dict[str, Any]
ContentReplacementRecord = dict[str, Any]
ToolResultReplacementRecord = dict[str, Any]
ToolResultCandidate = dict[str, Any]
CandidatePartition = dict[str, Any]

TOOL_RESULTS_SUBDIR = "tool-results"
PERSISTED_OUTPUT_TAG = "<persisted-output>"
PERSISTED_OUTPUT_CLOSING_TAG = "</persisted-output>"
TOOL_RESULT_CLEARED_MESSAGE = "[Old tool result content cleared]"
PREVIEW_SIZE_BYTES = 2000

DEFAULT_MAX_RESULT_SIZE_CHARS = 50_000
BYTES_PER_TOKEN = 4
MAX_TOOL_RESULT_BYTES = 100_000 * BYTES_PER_TOKEN
MAX_TOOL_RESULTS_PER_MESSAGE_CHARS = 200_000
_PERSIST_THRESHOLD_OVERRIDE_FLAG = "tengu_satin_quoll"
_MESSAGE_BUDGET_FLAG = "tengu_hawthorn_window"
_MESSAGE_BUDGET_ENABLED_FLAG = "tengu_hawthorn_steeple"


def _format_file_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def _sanitize_tool_name_for_analytics(tool_name: str) -> str:
    return "".join(ch for ch in str(tool_name) if ch.isalnum() or ch in {"_", "-"})[:128]


def _message_type(message: Any) -> Optional[str]:
    if isinstance(message, dict):
        return message.get("type")
    return getattr(message, "type", None)


def _message_content(message: Any) -> Any:
    payload = message.get("message") if isinstance(message, dict) else getattr(message, "message", None)
    if isinstance(payload, dict):
        return payload.get("content")
    return getattr(payload, "content", None)


def _assistant_message_id(message: Any) -> Optional[str]:
    payload = message.get("message") if isinstance(message, dict) else getattr(message, "message", None)
    if isinstance(payload, dict):
        return payload.get("id")
    return getattr(payload, "id", None)


def _block_type(block: Any) -> Optional[str]:
    if isinstance(block, dict):
        return block.get("type")
    return getattr(block, "type", None)


def _block_text(block: Any) -> Optional[str]:
    if isinstance(block, dict):
        return block.get("text")
    return getattr(block, "text", None)


def _tool_use_id(block: Any) -> Optional[str]:
    if isinstance(block, dict):
        return block.get("tool_use_id") or block.get("toolUseId") or block.get("id")
    return getattr(block, "tool_use_id", None) or getattr(block, "toolUseId", None) or getattr(block, "id", None)


def _tool_name(block: Any) -> Optional[str]:
    if isinstance(block, dict):
        return block.get("name")
    return getattr(block, "name", None)


def getPersistenceThreshold(toolName, declaredMaxResultSizeChars):
    if not math.isfinite(declaredMaxResultSizeChars):
        return declaredMaxResultSizeChars
    overrides = getFeatureValue_CACHED_MAY_BE_STALE(_PERSIST_THRESHOLD_OVERRIDE_FLAG, {})
    override = overrides.get(toolName) if isinstance(overrides, dict) else None
    if isinstance(override, (int, float)) and math.isfinite(override) and override > 0:
        return int(override)
    return min(int(declaredMaxResultSizeChars), DEFAULT_MAX_RESULT_SIZE_CHARS)


def getSessionDir():
    return str(Path(getProjectDir(getOriginalCwd())) / str(getSessionId()))


def getToolResultsDir():
    return str(Path(getSessionDir()) / TOOL_RESULTS_SUBDIR)


def getToolResultPath(id, isJson):
    ext = "json" if isJson else "txt"
    return str(Path(getToolResultsDir()) / f"{id}.{ext}")


async def ensureToolResultsDir():
    Path(getToolResultsDir()).mkdir(parents=True, exist_ok=True)


async def persistToolResult(content, toolUseId):
    is_json = isinstance(content, list)
    if is_json and any(_block_type(block) != "text" for block in content):
        return {"error": "Cannot persist tool results containing non-text content"}

    await ensureToolResultsDir()
    filepath = getToolResultPath(toolUseId, is_json)
    content_str = jsonStringify(content, indent=2) if is_json else str(content)

    try:
        with Path(filepath).open("x", encoding="utf-8") as handle:
            handle.write(content_str)
        logForDebugging(f"Persisted tool result to {filepath} ({_format_file_size(len(content_str))})")
    except FileExistsError:
        pass
    except Exception as error:
        logError(error)
        return {"error": getFileSystemErrorMessage(error)}

    preview = generatePreview(content_str, PREVIEW_SIZE_BYTES)
    return {
        "filepath": filepath,
        "originalSize": len(content_str),
        "isJson": is_json,
        "preview": preview["preview"],
        "hasMore": preview["hasMore"],
    }


def buildLargeToolResultMessage(result):
    message = f"{PERSISTED_OUTPUT_TAG}\n"
    message += f"Output too large ({_format_file_size(result['originalSize'])}). Full output saved to: {result['filepath']}\n\n"
    message += f"Preview (first {_format_file_size(PREVIEW_SIZE_BYTES)}):\n"
    message += result["preview"]
    message += "\n...\n" if result.get("hasMore") else "\n"
    message += PERSISTED_OUTPUT_CLOSING_TAG
    return message


async def processToolResultBlock(tool, toolUseResult, toolUseID):
    tool_result_block = tool.mapToolResultToToolResultBlockParam(toolUseResult, toolUseID)
    tool_name = getattr(tool, "name", None) or tool.get("name")
    max_result_size_chars = getattr(tool, "maxResultSizeChars", None) or tool.get("maxResultSizeChars") or DEFAULT_MAX_RESULT_SIZE_CHARS
    return await maybePersistLargeToolResult(
        tool_result_block,
        tool_name,
        getPersistenceThreshold(tool_name, max_result_size_chars),
    )


async def processPreMappedToolResultBlock(toolResultBlock, toolName, maxResultSizeChars):
    return await maybePersistLargeToolResult(
        toolResultBlock,
        toolName,
        getPersistenceThreshold(toolName, maxResultSizeChars),
    )


def isToolResultContentEmpty(content):
    if content is None:
        return True
    if isinstance(content, str):
        return content.strip() == ""
    if not isinstance(content, list):
        return False
    if len(content) == 0:
        return True
    return all(_block_type(block) == "text" and not str(_block_text(block) or "").strip() for block in content)


async def maybePersistLargeToolResult(toolResultBlock, toolName, persistenceThreshold=None):
    content = toolResultBlock.get("content") if isinstance(toolResultBlock, dict) else getattr(toolResultBlock, "content", None)
    if isToolResultContentEmpty(content):
        logEvent("tengu_tool_empty_result", {"toolName": _sanitize_tool_name_for_analytics(toolName)})
        if isinstance(toolResultBlock, dict):
            updated = dict(toolResultBlock)
            updated["content"] = f"({toolName} completed with no output)"
            return updated
        setattr(toolResultBlock, "content", f"({toolName} completed with no output)")
        return toolResultBlock
    if content is None or hasImageBlock(content):
        return toolResultBlock

    size = contentSize(content)
    threshold = MAX_TOOL_RESULT_BYTES if persistenceThreshold is None else persistenceThreshold
    if size <= threshold:
        return toolResultBlock

    result = await persistToolResult(content, _tool_use_id(toolResultBlock))
    if isPersistError(result):
        return toolResultBlock

    message = buildLargeToolResultMessage(result)
    logEvent(
        "tengu_tool_result_persisted",
        {
            "toolName": _sanitize_tool_name_for_analytics(toolName),
            "originalSizeBytes": result["originalSize"],
            "persistedSizeBytes": len(message),
            "estimatedOriginalTokens": math.ceil(result["originalSize"] / BYTES_PER_TOKEN),
            "estimatedPersistedTokens": math.ceil(len(message) / BYTES_PER_TOKEN),
            "thresholdUsed": threshold,
        },
    )
    if isinstance(toolResultBlock, dict):
        updated = dict(toolResultBlock)
        updated["content"] = message
        return updated
    setattr(toolResultBlock, "content", message)
    return toolResultBlock


def generatePreview(content, maxBytes):
    if len(content) <= maxBytes:
        return {"preview": content, "hasMore": False}
    truncated = content[:maxBytes]
    last_newline = truncated.rfind("\n")
    cut_point = last_newline if last_newline > maxBytes * 0.5 else maxBytes
    return {"preview": content[:cut_point], "hasMore": True}


def isPersistError(result):
    return isinstance(result, dict) and "error" in result


def createContentReplacementState():
    return {"seenIds": set(), "replacements": {}}


def cloneContentReplacementState(source):
    return {
        "seenIds": set(source.get("seenIds", set())),
        "replacements": dict(source.get("replacements", {})),
    }


def getPerMessageBudgetLimit():
    override = getFeatureValue_CACHED_MAY_BE_STALE(_MESSAGE_BUDGET_FLAG, None)
    if isinstance(override, (int, float)) and math.isfinite(override) and override > 0:
        return int(override)
    return MAX_TOOL_RESULTS_PER_MESSAGE_CHARS


def provisionContentReplacementState(initialMessages=None, initialContentReplacements=None):
    enabled = bool(getFeatureValue_CACHED_MAY_BE_STALE(_MESSAGE_BUDGET_ENABLED_FLAG, False))
    if not enabled:
        return None
    if initialMessages is not None:
        return reconstructContentReplacementState(initialMessages, initialContentReplacements or [])
    return createContentReplacementState()


def isContentAlreadyCompacted(content):
    return isinstance(content, str) and content.startswith(PERSISTED_OUTPUT_TAG)


def hasImageBlock(content):
    return isinstance(content, list) and any(_block_type(block) == "image" for block in content)


def contentSize(content):
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return sum(len(str(_block_text(block) or "")) for block in content if _block_type(block) == "text")
    return len(str(content))


def buildToolNameMap(messages):
    name_by_id: dict[str, str] = {}
    for message in messages or []:
        if _message_type(message) != "assistant":
            continue
        content = _message_content(message)
        if not isinstance(content, list):
            continue
        for block in content:
            if _block_type(block) == "tool_use":
                tool_use_id = _tool_use_id(block)
                name = _tool_name(block)
                if tool_use_id and name:
                    name_by_id[tool_use_id] = name
    return name_by_id


def collectCandidatesFromMessage(message):
    if _message_type(message) != "user":
        return []
    content = _message_content(message)
    if not isinstance(content, list):
        return []
    candidates: list[ToolResultCandidate] = []
    for block in content:
        if _block_type(block) != "tool_result":
            continue
        block_content = block.get("content") if isinstance(block, dict) else getattr(block, "content", None)
        if block_content is None or isContentAlreadyCompacted(block_content) or hasImageBlock(block_content):
            continue
        candidates.append({
            "toolUseId": _tool_use_id(block),
            "content": block_content,
            "size": contentSize(block_content),
        })
    return candidates


def collectCandidatesByMessage(messages):
    groups: list[list[ToolResultCandidate]] = []
    current: list[ToolResultCandidate] = []
    seen_assistant_ids: set[str] = set()

    def flush() -> None:
        nonlocal current
        if current:
            groups.append(current)
        current = []

    for message in messages or []:
        message_type = _message_type(message)
        if message_type == "user":
            current.extend(collectCandidatesFromMessage(message))
        elif message_type == "assistant":
            assistant_id = _assistant_message_id(message)
            if assistant_id and assistant_id in seen_assistant_ids:
                continue
            if assistant_id:
                seen_assistant_ids.add(assistant_id)
            flush()
    flush()
    return groups


def partitionByPriorDecision(candidates, state):
    replacements = state.get("replacements", {})
    seen_ids = state.get("seenIds", set())
    partition: CandidatePartition = {"mustReapply": [], "frozen": [], "fresh": []}
    for candidate in candidates:
        replacement = replacements.get(candidate["toolUseId"])
        if replacement is not None:
            partition["mustReapply"].append({**candidate, "replacement": replacement})
        elif candidate["toolUseId"] in seen_ids:
            partition["frozen"].append(candidate)
        else:
            partition["fresh"].append(candidate)
    return partition


def selectFreshToReplace(fresh, frozenSize, limit):
    sorted_fresh = sorted(fresh, key=lambda candidate: candidate["size"], reverse=True)
    remaining = frozenSize + sum(candidate["size"] for candidate in fresh)
    selected: list[ToolResultCandidate] = []
    for candidate in sorted_fresh:
        if remaining <= limit:
            break
        selected.append(candidate)
        remaining -= candidate["size"]
    return selected


def replaceToolResultContents(messages, replacementMap):
    replacement_map = dict(replacementMap)
    replaced_messages = []
    for message in messages or []:
        if _message_type(message) != "user":
            replaced_messages.append(message)
            continue
        content = _message_content(message)
        if not isinstance(content, list):
            replaced_messages.append(message)
            continue
        changed = False
        new_content = []
        for block in content:
            if _block_type(block) != "tool_result":
                new_content.append(block)
                continue
            replacement = replacement_map.get(_tool_use_id(block))
            if replacement is None:
                new_content.append(block)
                continue
            changed = True
            updated_block = dict(block) if isinstance(block, dict) else block
            if isinstance(updated_block, dict):
                updated_block["content"] = replacement
            else:
                setattr(updated_block, "content", replacement)
            new_content.append(updated_block)
        if not changed:
            replaced_messages.append(message)
        elif isinstance(message, dict) and isinstance(message.get("message"), dict):
            replaced_messages.append({**message, "message": {**message["message"], "content": new_content}})
        else:
            replaced_messages.append(message)
    return replaced_messages


async def buildReplacement(candidate):
    result = await persistToolResult(candidate["content"], candidate["toolUseId"])
    if isPersistError(result):
        return None
    return {"content": buildLargeToolResultMessage(result), "originalSize": result["originalSize"]}


async def enforceToolResultBudget(messages, state, skipToolNames=None):
    candidates_by_message = collectCandidatesByMessage(messages)
    name_by_tool_use_id = buildToolNameMap(messages) if skipToolNames else {}
    skip_tool_names = set(skipToolNames or set())
    limit = getPerMessageBudgetLimit()
    replacement_map: dict[str, str] = {}
    to_persist: list[ToolResultCandidate] = []

    for candidates in candidates_by_message:
        partition = partitionByPriorDecision(candidates, state)
        for candidate in partition["mustReapply"]:
            replacement_map[candidate["toolUseId"]] = candidate["replacement"]

        fresh = partition["fresh"]
        if not fresh:
            for candidate in candidates:
                state["seenIds"].add(candidate["toolUseId"])
            continue

        skipped = [candidate for candidate in fresh if name_by_tool_use_id.get(candidate["toolUseId"]) in skip_tool_names]
        eligible = [candidate for candidate in fresh if candidate not in skipped]
        for candidate in skipped:
            state["seenIds"].add(candidate["toolUseId"])

        frozen_size = sum(candidate["size"] for candidate in partition["frozen"])
        fresh_size = sum(candidate["size"] for candidate in eligible)
        selected = selectFreshToReplace(eligible, frozen_size, limit) if frozen_size + fresh_size > limit else []
        selected_ids = {candidate["toolUseId"] for candidate in selected}
        for candidate in candidates:
            if candidate["toolUseId"] not in selected_ids:
                state["seenIds"].add(candidate["toolUseId"])
        to_persist.extend(selected)

    newly_replaced: list[ToolResultReplacementRecord] = []
    if to_persist:
        replacements = await asyncio.gather(*(buildReplacement(candidate) for candidate in to_persist))
        replaced_size = 0
        for candidate, replacement in zip(to_persist, replacements):
            state["seenIds"].add(candidate["toolUseId"])
            if replacement is None:
                continue
            replacement_map[candidate["toolUseId"]] = replacement["content"]
            state["replacements"][candidate["toolUseId"]] = replacement["content"]
            replaced_size += replacement["originalSize"]
            newly_replaced.append({
                "kind": "tool-result",
                "toolUseId": candidate["toolUseId"],
                "replacement": replacement["content"],
            })
            logEvent(
                "tengu_tool_result_persisted_message_budget",
                {
                    "originalSizeBytes": replacement["originalSize"],
                    "persistedSizeBytes": len(replacement["content"]),
                    "estimatedOriginalTokens": math.ceil(replacement["originalSize"] / BYTES_PER_TOKEN),
                    "estimatedPersistedTokens": math.ceil(len(replacement["content"]) / BYTES_PER_TOKEN),
                },
            )
        if newly_replaced:
            logForDebugging(
                f"Per-message budget: persisted {len(newly_replaced)} tool results, shed ~{_format_file_size(replaced_size)}"
            )
    if not replacement_map:
        return {"messages": messages, "newlyReplaced": []}
    return {"messages": replaceToolResultContents(messages, replacement_map), "newlyReplaced": newly_replaced}


async def applyToolResultBudget(messages, state, writeToTranscript=None, skipToolNames=None):
    if not state:
        return messages
    result = await enforceToolResultBudget(messages, state, skipToolNames)
    if result["newlyReplaced"] and writeToTranscript is not None:
        writeToTranscript(result["newlyReplaced"])
    return result["messages"]


def reconstructContentReplacementState(messages, records, inheritedReplacements=None):
    state = createContentReplacementState()
    candidate_ids = {candidate["toolUseId"] for group in collectCandidatesByMessage(messages) for candidate in group}
    for tool_use_id in candidate_ids:
        state["seenIds"].add(tool_use_id)
    for record in records or []:
        if record.get("kind") == "tool-result" and record.get("toolUseId") in candidate_ids:
            state["replacements"][record["toolUseId"]] = record["replacement"]
    if inheritedReplacements:
        for tool_use_id in candidate_ids:
            if tool_use_id not in state["replacements"] and tool_use_id in inheritedReplacements:
                state["replacements"][tool_use_id] = inheritedReplacements[tool_use_id]
    return state


def reconstructForSubagentResume(parentState, resumedMessages, sidechainRecords):
    inherited = dict((parentState or {}).get("replacements", {}))
    return reconstructContentReplacementState(resumedMessages, sidechainRecords or [], inherited)


def getFileSystemErrorMessage(error):
    message = str(error).strip() or "Unknown filesystem error"
    return f"Failed to persist tool result: {message}"


get_persistence_threshold = getPersistenceThreshold
get_session_dir = getSessionDir
get_tool_results_dir = getToolResultsDir
get_tool_result_path = getToolResultPath
ensure_tool_results_dir = ensureToolResultsDir
persist_tool_result = persistToolResult
build_large_tool_result_message = buildLargeToolResultMessage
process_tool_result_block = processToolResultBlock
process_pre_mapped_tool_result_block = processPreMappedToolResultBlock
is_tool_result_content_empty = isToolResultContentEmpty
maybe_persist_large_tool_result = maybePersistLargeToolResult
generate_preview = generatePreview
is_persist_error = isPersistError
create_content_replacement_state = createContentReplacementState
clone_content_replacement_state = cloneContentReplacementState
get_per_message_budget_limit = getPerMessageBudgetLimit
provision_content_replacement_state = provisionContentReplacementState
is_content_already_compacted = isContentAlreadyCompacted
has_image_block = hasImageBlock
content_size = contentSize
build_tool_name_map = buildToolNameMap
collect_candidates_from_message = collectCandidatesFromMessage
collect_candidates_by_message = collectCandidatesByMessage
partition_by_prior_decision = partitionByPriorDecision
select_fresh_to_replace = selectFreshToReplace
replace_tool_result_contents = replaceToolResultContents
build_replacement = buildReplacement
enforce_tool_result_budget = enforceToolResultBudget
apply_tool_result_budget = applyToolResultBudget
reconstruct_content_replacement_state = reconstructContentReplacementState
reconstruct_for_subagent_resume = reconstructForSubagentResume
get_file_system_error_message = getFileSystemErrorMessage


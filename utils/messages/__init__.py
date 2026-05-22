"""Message utilities — mirrors src/utils/messages.ts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ..sessionTitle import extractConversationText

SYNTHETIC_MODEL = "<synthetic>"
INTERRUPT_MESSAGE = "[Request interrupted by user]"
INTERRUPT_MESSAGE_FOR_TOOL_USE = "[Request interrupted by user for tool use]"
NO_CONTENT_MESSAGE = "(no content)"
CANCEL_MESSAGE = "The user doesn't want to take this action right now. STOP what you are doing and wait for the user to tell you how to proceed."
REJECT_MESSAGE = "The user doesn't want to proceed with this tool use. The tool use was rejected (eg. if it was a file edit, the new_string was NOT written to the file). STOP what you are doing and wait for the user to tell you how to proceed."
NO_RESPONSE_REQUESTED = "No response requested."
SYNTHETIC_MESSAGES = {
	INTERRUPT_MESSAGE,
	INTERRUPT_MESSAGE_FOR_TOOL_USE,
	CANCEL_MESSAGE,
	REJECT_MESSAGE,
	NO_RESPONSE_REQUESTED,
}


def is_assistant_message(message: Any) -> bool:
	if isinstance(message, dict):
		return message.get("role") == "assistant"
	if message is None:
		return False
	return True


def is_human_message(message: Any) -> bool:
	if isinstance(message, dict):
		return message.get("role") == "user"
	if message is None:
		return False
	return True


def strip_prompt_xml_tags(text: str) -> str:
	import re

	return re.sub(r"</?(?:command-name|ide_opened_file|ide_cursor_position)[^>]*>", "", text)


def createUserMessage(payload: dict[str, Any]) -> dict[str, Any]:
	content = payload.get("content")
	message_content = content if content not in (None, "") else NO_CONTENT_MESSAGE
	message = {
		"role": "user",
		"content": message_content,
	}
	result = {
		"role": "user",
		"type": "user",
		"message": message,
		"content": message_content,
		"uuid": payload.get("uuid") or str(uuid4()),
		"timestamp": payload.get("timestamp") or datetime.now(timezone.utc).isoformat(),
	}
	for key in (
		"isMeta",
		"isVisibleInTranscriptOnly",
		"isVirtual",
		"isCompactSummary",
		"summarizeMetadata",
		"toolUseResult",
		"mcpMeta",
		"imagePasteIds",
		"sourceToolAssistantUUID",
		"permissionMode",
		"origin",
	):
		if key in payload and payload.get(key) is not None:
			result[key] = payload.get(key)
	return result


def getAssistantMessageText(message: Any) -> str:
	if isinstance(message, dict):
		if isinstance(message.get("text"), str):
			return message["text"]
		nested = message.get("message")
		if isinstance(nested, dict):
			content = nested.get("content")
			if isinstance(content, str):
				return content
			if isinstance(content, list):
				parts: list[str] = []
				for block in content:
					if isinstance(block, dict) and isinstance(block.get("text"), str):
						parts.append(block["text"])
				return "".join(parts)
	return ""


def getMessagesAfterCompactBoundary(messages: list[Any], options: dict[str, Any] | None = None) -> list[Any]:
	del options
	boundary_index = -1
	for index in range(len(messages or []) - 1, -1, -1):
		msg = messages[index]
		if isinstance(msg, dict) and msg.get("type") == "system" and msg.get("subtype") == "compact_boundary":
			boundary_index = index
			break
	return list(messages if boundary_index == -1 else messages[boundary_index:])


def normalizeMessagesForAPI(messages: list[Any], tools: list[Any] | None = None) -> list[dict[str, Any]]:
	del tools
	normalized: list[dict[str, Any]] = []
	for msg in messages or []:
		if not isinstance(msg, dict):
			continue
		msg_type = msg.get("type") or msg.get("role")
		if msg_type not in ("user", "assistant"):
			continue
		if msg.get("isVirtual"):
			continue
		normalized.append(msg)
	return normalized


create_user_message = createUserMessage
get_assistant_message_text = getAssistantMessageText
extract_conversation_text = extractConversationText
get_messages_after_compact_boundary = getMessagesAfterCompactBoundary
normalize_messages_for_api = normalizeMessagesForAPI

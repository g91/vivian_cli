"""Main entrypoint for Vivian Agent SDK types and helpers.

Python port of src/entrypoints/agentSdkTypes.ts.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import os
import uuid
from pathlib import Path
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Awaitable, Callable, TypedDict

from .sdk.coreTypes import *  # noqa: F401,F403
from ..types import Message


class AbortError(Exception):
	"""Raised when an SDK operation is aborted."""


class CronTask(TypedDict, total=False):
	id: str
	cron: str
	prompt: str
	createdAt: int
	recurring: bool


class CronJitterConfig(TypedDict, total=False):
	recurringFrac: float
	recurringCapMs: int
	oneShotMaxMs: int
	oneShotFloorMs: int
	oneShotMinuteMod: int
	recurringMaxAgeMs: int


class ScheduledTaskEvent(TypedDict, total=False):
	type: str
	task: CronTask
	tasks: list[CronTask]


@dataclass(slots=True)
class ScheduledTasksHandle:
	_queue: asyncio.Queue[ScheduledTaskEvent]
	_scheduler: dict[str, Any]

	async def events(self) -> AsyncGenerator[ScheduledTaskEvent, None]:
		while True:
			event = await self._queue.get()
			yield event

	def getNextFireTime(self) -> int | None:
		return self._scheduler.get("getNextFireTime", lambda: None)()


def tool(
	name: str,
	description: str,
	inputSchema: Any,
	handler: Callable[[Any, Any], Awaitable[dict[str, Any]]],
	extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
	return {
		"name": name,
		"description": description,
		"inputSchema": inputSchema,
		"handler": handler,
		"annotations": (extras or {}).get("annotations"),
		"searchHint": (extras or {}).get("searchHint"),
		"alwaysLoad": bool((extras or {}).get("alwaysLoad", False)),
	}


def createSdkMcpServer(options: dict[str, Any]) -> dict[str, Any]:
	return {
		"type": "sdk",
		"name": options["name"],
		"version": options.get("version", "0.0.0"),
		"tools": list(options.get("tools", [])),
		"instance": options,
	}


def _build_engine(options: dict[str, Any] | None = None):
	from ..api.client import VivianClient
	from ..constants import DEFAULT_BASE_URL, DEFAULT_MODEL
	from ..query_engine import QueryEngine

	options = options or {}
	client = VivianClient(
		api_key=options.get("apiKey") or os.environ.get("VIVIAN_API_KEY"),
		admin_jwt=options.get("adminJwt"),
		base_url=options.get("baseUrl", DEFAULT_BASE_URL),
		default_model=options.get("model", DEFAULT_MODEL),
	)
	return QueryEngine(
		client,
		model=options.get("model", DEFAULT_MODEL),
		cwd=options.get("cwd", "."),
		custom_system_prompt=options.get("systemPrompt"),
		append_system_prompt=options.get("appendSystemPrompt"),
		max_turns=int(options.get("maxTurns", 25)),
	)


def _run_awaitable_sync(awaitable: Any) -> Any:
	try:
		loop = asyncio.get_event_loop()
		if loop.is_running():
			with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
				future = pool.submit(asyncio.run, awaitable)
				return future.result()
		return loop.run_until_complete(awaitable)
	except RuntimeError:
		return asyncio.run(awaitable)


def _sdk_message_to_engine_message(message: dict[str, Any]) -> Message:
	payload = message.get("message") if isinstance(message.get("message"), dict) else {}
	return Message(
		role=str(message.get("role") or message.get("type") or "user"),
		content=message.get("content") if message.get("content") is not None else payload.get("content"),
		tool_calls=(
			message.get("tool_calls")
			or message.get("toolCalls")
			or payload.get("tool_calls")
			or payload.get("toolCalls")
		),
		tool_call_id=(
			message.get("tool_call_id")
			or message.get("toolCallId")
			or payload.get("tool_call_id")
			or payload.get("toolCallId")
		),
		name=message.get("name") or payload.get("name"),
	)


def _last_transcript_uuid(messages: list[dict[str, Any]]) -> str | None:
	for message in reversed(messages):
		if isinstance(message, dict) and isinstance(message.get("uuid"), str):
			return str(message["uuid"])
	return None


def _hydrate_engine_from_resume(engine: Any, session_data: dict[str, Any]) -> None:
	from ..bootstrap.state import switchSession
	from ..utils.sessionRestore import processResumedConversation

	processed = _run_awaitable_sync(
		processResumedConversation(
			session_data,
			{
				"currentCwd": getattr(engine, "cwd", None),
				"cliAgents": [],
				"initialState": engine.state_store.get_state(),
				"agentDefinitions": engine.state_store.get_state().get("agentDefinitions"),
				"mainThreadAgentDefinition": None,
			},
			{"forkSession": False, "includeAttribution": True},
		)
	)
	messages = [
		_sdk_message_to_engine_message(message)
		for message in processed.get("messages", session_data.get("messages", []))
		if isinstance(message, dict)
	]
	raw_messages = processed.get("messages", session_data.get("messages", []))
	full_path = session_data.get("fullPath") or processed.get("fullPath")
	if session_data.get("sessionId"):
		switchSession(str(session_data.get("sessionId")), str(Path(full_path).parent) if full_path else None)
	engine.messages = messages
	engine.session_id = str(session_data.get("sessionId") or engine.session_id)
	setattr(engine, "_last_transcript_uuid", _last_transcript_uuid(raw_messages))
	engine.turn_count = sum(1 for message in messages if message.role == "user")
	engine.state_store.set_state(lambda _prev: processed.get("initialState") or _prev)


async def _load_sdk_resume_session(session_id: str, options: dict[str, Any] | None) -> dict[str, Any] | None:
	from ..utils.conversationRecovery import loadConversationForResume
	from ..utils.sessionStoragePortable import resolveSessionFilePath

	options = options or {}
	resolved = await resolveSessionFilePath(session_id, options.get("dir"))
	if resolved:
		return await loadConversationForResume(None, resolved.get("filePath"))
	return await loadConversationForResume(session_id, None)


async def _collect_async_prompt(prompt: Any) -> str:
	if isinstance(prompt, str):
		return prompt
	chunks: list[str] = []
	async for item in prompt:
		if isinstance(item, dict):
			chunks.append(str(item.get("content", "")))
		else:
			chunks.append(str(item))
	return "\n".join(chunk for chunk in chunks if chunk)


def query(*_args: Any, **_kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
	params = (_args[0] if _args else None) or _kwargs

	async def _runner() -> AsyncGenerator[dict[str, Any], None]:
		prompt = await _collect_async_prompt(params.get("prompt", ""))
		engine = _build_engine(params.get("options"))
		async for event in engine.submit_message(prompt):
			if isinstance(event, dict):
				yield event
			else:
				yield {"type": type(event).__name__, "value": event}

	return _runner()


@dataclass(slots=True)
class SDKSession:
	sessionId: str
	engine: Any

	async def prompt(self, message: str) -> list[dict[str, Any]]:
		events: list[dict[str, Any]] = []
		async for event in self.engine.submit_message(message):
			if isinstance(event, dict):
				events.append(event)
			else:
				events.append({"type": type(event).__name__, "value": event})
		return events


def unstable_v2_createSession(_options: dict[str, Any]) -> SDKSession:
	return SDKSession(sessionId=str(uuid.uuid4()), engine=_build_engine(_options))


def unstable_v2_resumeSession(_sessionId: str, _options: dict[str, Any]) -> SDKSession:
	engine = _build_engine(_options)
	resumed = _run_awaitable_sync(_load_sdk_resume_session(_sessionId, _options))
	if resumed is not None:
		_hydrate_engine_from_resume(engine, resumed)
	return SDKSession(sessionId=str(getattr(engine, "session_id", _sessionId)), engine=engine)


async def unstable_v2_prompt(_message: str, _options: dict[str, Any]) -> dict[str, Any]:
	engine = _build_engine(_options)
	last_event: dict[str, Any] | None = None
	async for event in engine.submit_message(_message):
		if isinstance(event, dict):
			last_event = event
		else:
			last_event = {"type": type(event).__name__, "value": event}
	return last_event or {"type": "result", "value": None}


async def getSessionMessages(_sessionId: str, _options: dict[str, Any] | None = None) -> list[dict[str, Any]]:
	from ..utils.sessionStorage import buildConversationChain, findLatestMessage, loadTranscriptFile, removeExtraFields
	from ..utils.sessionStoragePortable import resolveSessionFilePath

	options = _options or {}
	include_system_messages = bool(options.get("includeSystemMessages", False))
	resolved = await resolveSessionFilePath(_sessionId, options.get("dir"))
	if not resolved:
		return []

	loaded = await loadTranscriptFile(resolved["filePath"])
	by_uuid = loaded.get("messages", {})
	leaf_uuids = loaded.get("leafUuids", set())
	if not by_uuid:
		return []

	tip = findLatestMessage(
		by_uuid.values(),
		lambda message: message.get("uuid") in leaf_uuids and not message.get("isSidechain"),
	)
	if not tip:
		return []

	transcript = removeExtraFields(buildConversationChain(by_uuid, tip))
	messages: list[dict[str, Any]] = []
	for entry in transcript:
		if not isinstance(entry, dict) or entry.get("isSidechain"):
			continue
		entry_type = entry.get("type")
		if entry_type not in {"user", "assistant", "system"}:
			continue
		if entry_type == "system" and not include_system_messages:
			continue

		message = entry.get("message")
		content = None
		tool_calls = None
		tool_call_id = None
		name = None

		if isinstance(message, dict):
			content = message.get("content")
			tool_calls = message.get("tool_calls") or message.get("toolCalls")
			tool_call_id = message.get("tool_call_id") or message.get("toolCallId")
			name = message.get("name")
		elif isinstance(message, str):
			content = message

		messages.append(
			{
				"role": entry_type,
				"content": content,
				"tool_calls": tool_calls,
				"tool_call_id": tool_call_id,
				"name": name,
			}
		)

	offset = int(options.get("offset", 0) or 0)
	limit = options.get("limit")
	if offset > 0:
		messages = messages[offset:]
	if isinstance(limit, int) and limit >= 0:
		messages = messages[:limit]
	return messages


def _normalize_sdk_session_info(info: dict[str, Any] | None) -> dict[str, Any] | None:
	if info is None:
		return None
	if info.get("summary") and "title" not in info:
		info = dict(info)
		info["title"] = info["summary"]
	return info


async def listSessions(_options: dict[str, Any] | None = None) -> list[dict[str, Any]]:
	from ..utils.listSessionsImpl import listSessionsImpl

	options = dict(_options or {})
	if "limit" in options:
		try:
			options["limit"] = int(options["limit"])
		except (TypeError, ValueError):
			options.pop("limit", None)
	if "offset" in options:
		try:
			options["offset"] = int(options["offset"])
		except (TypeError, ValueError):
			options["offset"] = 0

	sessions = await listSessionsImpl(options)
	return [_normalize_sdk_session_info(session) for session in sessions if session is not None]


async def getSessionInfo(_sessionId: str, _options: dict[str, Any] | None = None) -> dict[str, Any] | None:
	from ..utils.listSessionsImpl import getSessionInfoImpl

	info = await getSessionInfoImpl(_sessionId, _options or {})
	return _normalize_sdk_session_info(info)


async def _append_session_metadata_entry(
	_sessionId: str,
	entry: dict[str, Any],
	_options: dict[str, Any] | None = None,
) -> None:
	from ..utils.sessionStoragePortable import resolveSessionFilePath

	resolved = await resolveSessionFilePath(_sessionId, (_options or {}).get("dir"))
	if not resolved:
		raise FileNotFoundError(f"Session {_sessionId} not found")

	with open(resolved["filePath"], "a", encoding="utf-8") as handle:
		handle.write(json.dumps(entry, separators=(",", ":")) + "\n")


async def renameSession(_sessionId: str, _title: str, _options: dict[str, Any] | None = None) -> None:
	await _append_session_metadata_entry(
		_sessionId,
		{"type": "custom-title", "customTitle": _title, "sessionId": _sessionId},
		_options,
	)


async def tagSession(_sessionId: str, _tag: str | None, _options: dict[str, Any] | None = None) -> None:
	await _append_session_metadata_entry(
		_sessionId,
		{"type": "tag", "tag": _tag or "", "sessionId": _sessionId},
		_options,
	)


_FORK_METADATA_ENTRY_TYPES = {
	"custom-title",
	"tag",
	"agent-name",
	"agent-color",
	"agent-setting",
	"mode",
	"pr-link",
	"content-replacement",
}


def _remap_fork_entry(entry: dict[str, Any], new_session_id: str, uuid_map: dict[str, str]) -> dict[str, Any]:
	updated = dict(entry)
	updated["sessionId"] = new_session_id
	if isinstance(updated.get("uuid"), str):
		updated["uuid"] = uuid_map.get(updated["uuid"], updated["uuid"])
	if isinstance(updated.get("parentUuid"), str):
		updated["parentUuid"] = uuid_map.get(updated["parentUuid"], updated["parentUuid"])
	if isinstance(updated.get("logicalParentUuid"), str):
		updated["logicalParentUuid"] = uuid_map.get(updated["logicalParentUuid"], updated["logicalParentUuid"])
	if updated.get("type") == "summary" and isinstance(updated.get("leafUuid"), str):
		updated["leafUuid"] = uuid_map.get(updated["leafUuid"], updated["leafUuid"])
	return updated


async def _load_fork_source(session_id: str, options: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
	from ..utils.conversationRecovery import loadMessagesFromJsonlPath
	from ..utils.sessionStorage import buildConversationChain, findLatestMessage, loadTranscriptFile
	from ..utils.sessionStoragePortable import resolveSessionFilePath

	resolved = await resolveSessionFilePath(session_id, options.get("dir"))
	if not resolved:
		raise FileNotFoundError(f"Session {session_id} not found")

	file_path = resolved["filePath"]
	loaded = await loadTranscriptFile(file_path)
	messages_by_uuid = loaded.get("messages", {})
	if not messages_by_uuid:
		raise FileNotFoundError(f"Session {session_id} is empty")

	up_to_message_id = options.get("upToMessageId")
	if up_to_message_id:
		tip = messages_by_uuid.get(up_to_message_id)
		if not isinstance(tip, dict):
			raise FileNotFoundError(f"Message {up_to_message_id} not found in session {session_id}")
	else:
		leaf_uuids = loaded.get("leafUuids", set())
		tip = findLatestMessage(
			messages_by_uuid.values(),
			lambda message: message.get("uuid") in leaf_uuids and not message.get("isSidechain"),
		)
		if not tip:
			raise FileNotFoundError(f"Session {session_id} has no resumable conversation chain")

	chain = buildConversationChain(messages_by_uuid, tip)
	selected = {message.get("uuid") for message in chain if isinstance(message, dict) and isinstance(message.get("uuid"), str)}
	loaded_log = await loadMessagesFromJsonlPath(file_path)

	entries: list[dict[str, Any]] = []
	with open(file_path, "r", encoding="utf-8") as handle:
		for line in handle:
			line = line.strip()
			if not line:
				continue
			try:
				entry = json.loads(line)
			except Exception:
				continue
			if isinstance(entry, dict):
				entries.append(entry)

	return resolved, entries, {"loaded": loaded_log, "selectedUuids": selected}


async def forkSession(_sessionId: str, _options: dict[str, Any] | None = None) -> dict[str, Any]:
	options = _options or {}
	new_session_id = str(uuid.uuid4())
	resolved, entries, fork_context = await _load_fork_source(_sessionId, options)
	selected_uuids = fork_context["selectedUuids"]
	loaded_log = fork_context["loaded"]
	uuid_map = {
		uuid_value: str(uuid.uuid4())
		for uuid_value in selected_uuids
		if isinstance(uuid_value, str)
	}

	target_path = os.path.join(os.path.dirname(resolved["filePath"]), f"{new_session_id}.jsonl")
	with open(target_path, "w", encoding="utf-8") as handle:
		for entry in entries:
			entry_type = entry.get("type")
			if isinstance(entry.get("uuid"), str):
				if entry["uuid"] not in selected_uuids:
					continue
				handle.write(json.dumps(_remap_fork_entry(entry, new_session_id, uuid_map), separators=(",", ":")) + "\n")
				continue
			if entry.get("sessionId") != _sessionId or entry_type not in _FORK_METADATA_ENTRY_TYPES:
				continue
			if entry_type == "custom-title" and options.get("title"):
				continue
			handle.write(json.dumps(_remap_fork_entry(entry, new_session_id, uuid_map), separators=(",", ":")) + "\n")

		if options.get("title"):
			handle.write(
				json.dumps(
					{"type": "custom-title", "customTitle": options["title"], "sessionId": new_session_id},
					separators=(",", ":"),
				)
				+ "\n"
			)

	try:
		from ..utils.plans import copyPlanForFork

		await copyPlanForFork(loaded_log, new_session_id)
	except Exception:
		pass

	return {"sessionId": new_session_id}


def watchScheduledTasks(opts: dict[str, Any]) -> ScheduledTasksHandle:
	from ..utils.cronScheduler import createCronScheduler

	queue: asyncio.Queue[ScheduledTaskEvent] = asyncio.Queue()
	loop = asyncio.get_event_loop()

	def _emit(event: ScheduledTaskEvent) -> None:
		loop.call_soon_threadsafe(queue.put_nowait, event)

	signal = opts.get("signal")
	scheduler = createCronScheduler(
		{
			"dir": opts["dir"],
			"lockIdentity": opts.get("dir"),
			"getJitterConfig": opts.get("getJitterConfig"),
			"isKilled": lambda: bool(signal.is_set()) if hasattr(signal, "is_set") else False,
			"onFireTask": lambda task: _emit({"type": "fire", "task": task}),
			"onMissed": lambda tasks: _emit({"type": "missed", "tasks": tasks}),
		}
	)
	scheduler["start"]()
	return ScheduledTasksHandle(queue, scheduler)


def buildMissedTaskNotification(missed: list[CronTask]) -> str:
	from ..utils.cronScheduler import buildMissedTaskNotification as _build

	return _build(missed)


async def connectRemoteControl(_opts: dict[str, Any]) -> Any:
	raise RuntimeError("connectRemoteControl is unavailable in the Python SDK entrypoint")


AgentSdkTypes = dict[str, Any]

__all__ = [name for name in list(globals()) if not name.startswith("_")]

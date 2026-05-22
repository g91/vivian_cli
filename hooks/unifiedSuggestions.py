"""Unified suggestions mirroring src/hooks/unifiedSuggestions.ts."""

from __future__ import annotations

from difflib import SequenceMatcher
import os
from typing import Any

from .fileSuggestions import generateFileSuggestions

try:
	from ..tools.AgentTool.agentColorManager import getAgentColor
except Exception:
	def getAgentColor(_agent_id: str) -> str:  # type: ignore[no-redef]
		return "default"


MAX_UNIFIED_SUGGESTIONS = 15
DESCRIPTION_MAX_LENGTH = 60


def _truncate(text: str, max_len: int = DESCRIPTION_MAX_LENGTH) -> str:
	if len(text) <= max_len:
		return text
	return text[: max_len - 1] + "..."


def _ratio(query: str, value: str) -> float:
	if not query:
		return 1.0
	return SequenceMatcher(None, query.lower(), value.lower()).ratio()


def _create_suggestion_from_source(source: dict[str, Any]) -> dict[str, Any]:
	stype = source["type"]
	if stype == "file":
		return {
			"id": f"file-{source['path']}",
			"displayText": source["displayText"],
			"description": source.get("description"),
		}
	if stype == "mcp_resource":
		return {
			"id": f"mcp-resource-{source['server']}__{source['uri']}",
			"displayText": source["displayText"],
			"description": source["description"],
		}
	return {
		"id": f"agent-{source['agentType']}",
		"displayText": source["displayText"],
		"description": source["description"],
		"color": source.get("color"),
	}


def _generate_agent_suggestions(
	agents: list[dict[str, Any]],
	query: str,
	showOnEmpty: bool = False,
) -> list[dict[str, Any]]:
	if not query and not showOnEmpty:
		return []

	out: list[dict[str, Any]] = []
	q = query.lower()
	for agent in agents:
		agent_type = str(agent.get("agentType") or agent.get("name") or "")
		when_to_use = str(agent.get("whenToUse") or agent.get("description") or "")
		if not agent_type:
			continue
		if q and q not in agent_type.lower() and q not in when_to_use.lower():
			continue
		out.append(
			{
				"type": "agent",
				"displayText": f"{agent_type} (agent)",
				"description": _truncate(when_to_use),
				"agentType": agent_type,
				"color": getAgentColor(agent_type),
			},
		)
	return out


async def generateUnifiedSuggestions(
	query: str,
	mcpResources: dict[str, list[dict[str, Any]]],
	agents: list[dict[str, Any]],
	showOnEmpty: bool = False,
) -> list[dict[str, Any]]:
	if not query and not showOnEmpty:
		return []

	file_suggestions = generateFileSuggestions(query, showOnEmpty)
	agent_sources = _generate_agent_suggestions(agents, query, showOnEmpty)

	file_sources: list[dict[str, Any]] = []
	for suggestion in file_suggestions:
		text = str(suggestion.get("displayText") or "")
		file_sources.append(
			{
				"type": "file",
				"displayText": text,
				"description": suggestion.get("description"),
				"path": text,
				"filename": os.path.basename(text),
				"score": float((suggestion.get("metadata") or {}).get("score", 0.5)),
			},
		)

	mcp_sources: list[dict[str, Any]] = []
	for resources in mcpResources.values():
		for resource in resources:
			server = str(resource.get("server") or "")
			uri = str(resource.get("uri") or "")
			name = str(resource.get("name") or uri)
			description = str(resource.get("description") or name or uri)
			mcp_sources.append(
				{
					"type": "mcp_resource",
					"displayText": f"{server}:{uri}",
					"description": _truncate(description),
					"server": server,
					"uri": uri,
					"name": name,
				},
			)

	if not query:
		all_sources = [*file_sources, *mcp_sources, *agent_sources]
		return [_create_suggestion_from_source(s) for s in all_sources[:MAX_UNIFIED_SUGGESTIONS]]

	scored: list[tuple[float, dict[str, Any]]] = []
	for file_source in file_sources:
		scored.append((file_source.get("score", 0.5), file_source))

	non_file_sources = [*mcp_sources, *agent_sources]
	for source in non_file_sources:
		text_score = _ratio(query, str(source.get("displayText", "")))
		desc_score = _ratio(query, str(source.get("description", "")))
		combined = max(text_score, desc_score)
		# Normalize so lower score is better, like Fuse/nucleo behavior.
		scored.append((1.0 - combined, source))

	scored.sort(key=lambda item: item[0])
	top = [src for _score, src in scored[:MAX_UNIFIED_SUGGESTIONS]]
	return [_create_suggestion_from_source(s) for s in top]


generate_unified_suggestions = generateUnifiedSuggestions

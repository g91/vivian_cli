"""memory command — mirrors src/commands/memory/memory.tsx.

Query and manage Vivian's persistent memory across sessions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def _format_service_memories(core: list[dict] | None = None, episodic: list[dict] | None = None) -> str:
    lines: list[str] = []
    if core:
        lines.append("Core Memory:")
        for memory in core[:10]:
            lines.append(
                f"  [{memory.get('category', '')}] {memory.get('key', '')}: {memory.get('value', '')}"
            )
    if episodic:
        lines.append("Recent Episodic Memory:")
        for memory in episodic[:5]:
            lines.append(f"  {memory.get('summary', memory.get('content', ''))[:100]}")
    return "\n".join(lines) if lines else "No memories stored."


async def formatMemory(context: CommandContext) -> str:
    """Format memory information."""
    memory_service = getattr(context, "memory_service", None)
    try:
        if memory_service is None:
            client = getattr(context, "client", None)
            if client is not None:
                from ...services.memory_service import MemoryService

                memory_service = MemoryService(client)
        if memory_service is not None:
            core = await memory_service.get_core_memories()
            episodic = await memory_service.get_episodic_memories(limit=5)
            return _format_service_memories(core, episodic)
    except Exception:
        pass

    lines: list[str] = []
    try:
        from ...memdir import get_memories

        memories = get_memories()
        if memories:
            lines.append("Persistent Memory:")
            for m in memories[:15]:
                key = getattr(m, "key", m.get("key", "")) if not isinstance(m, str) else m
                val = getattr(m, "value", m.get("value", "")) if not isinstance(m, str) else ""
                lines.append(f"  • {key}: {val}")
    except Exception:
        pass
    return "\n".join(lines) if lines else "No memories stored."


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    query = args.strip() if args else ""
    if query:
        memory_service = getattr(context, "memory_service", None)
        try:
            if memory_service is None:
                client = getattr(context, "client", None)
                if client is not None:
                    from ...services.memory_service import MemoryService

                    memory_service = MemoryService(client)
            if memory_service is not None and hasattr(memory_service, "get_relevant_memories"):
                results = await memory_service.get_relevant_memories(query)
                if results:
                    core = [item for item in results if isinstance(item, dict) and (item.get("key") or item.get("category"))]
                    episodic = [item for item in results if isinstance(item, dict) and not (item.get("key") or item.get("category"))]
                    return TextResult(_format_service_memories(core, episodic))
            from ...memdir import search_memories

            results = search_memories(query)
            if results:
                lines = [f"Memory search: \"{query}\"", ""]
                for r in results[:10]:
                    lines.append(f"  • {r}")
                return TextResult("\n".join(lines))
        except Exception:
            pass
        return TextResult(f"No memories matching: {query}")
    result = await formatMemory(context)
    return TextResult(result)


format_memory = formatMemory

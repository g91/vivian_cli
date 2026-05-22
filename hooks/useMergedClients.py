"""Port of src/hooks/useMergedClients.ts."""
from __future__ import annotations

from typing import Any


def mergeClients(initialClients: list[dict] | None, mcpClients: list[dict] | None) -> list[dict]:
    if initialClients and mcpClients and len(mcpClients) > 0:
        merged = [*initialClients, *mcpClients]
        seen: set[Any] = set()
        deduped: list[dict] = []
        for client in merged:
            key = client.get('name') if isinstance(client, dict) else None
            if key in seen:
                continue
            seen.add(key)
            deduped.append(client)
        return deduped
    return initialClients or []


def useMergedClients(initialClients: list[dict] | None, mcpClients: list[dict] | None) -> list[dict]:
    return mergeClients(initialClients, mcpClients)

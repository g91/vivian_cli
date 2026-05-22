"""Query dependencies — mirrors src/query/deps.ts.

Provides a QueryDeps bundle of production implementations so tests can swap
in fakes for any single dependency.
"""
from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class QueryDeps:
    callModel: Callable[..., Any]
    microcompact: Callable[..., Any]
    autocompact: Callable[..., Any]
    uuid: Callable[[], str] = field(default_factory=lambda: lambda: str(_uuid.uuid4()))


def productionDeps() -> QueryDeps:
    """Return QueryDeps wired to production implementations."""
    try:
        from vivian_cli.services.api.vivian import queryModelWithoutStreaming as _callModel
    except ImportError:
        async def _callModel(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
            raise NotImplementedError("callModel not available")

    try:
        from vivian_cli.services.compact_service import CompactService

        _compact_service = CompactService()

        async def _micro(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
            return _compact_service.micro_compact(*args, **kwargs)

        async def _auto(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
            return await _compact_service.compact(*args, **kwargs)
    except ImportError:
        async def _micro(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
            raise NotImplementedError("microcompact not available")
        async def _auto(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
            raise NotImplementedError("autocompact not available")

    return QueryDeps(
        callModel=_callModel,
        microcompact=_micro,
        autocompact=_auto,
        uuid=lambda: str(_uuid.uuid4()),
    )

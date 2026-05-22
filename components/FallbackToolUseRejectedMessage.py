"""Fallback tool rejection component — mirrors src/components/FallbackToolUseRejectedMessage.tsx."""

from __future__ import annotations

from .InterruptedByUser import InterruptedByUser
from .MessageResponse import MessageResponse


def FallbackToolUseRejectedMessage() -> list[str]:
    return MessageResponse(children=InterruptedByUser(), height=1).render_lines()


__all__ = ["FallbackToolUseRejectedMessage"]
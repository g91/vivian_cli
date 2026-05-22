"""REPL screen — mirrors src/screens/REPL.tsx.

The main interactive REPL (Read-Eval-Print Loop) screen.
In Python this is a data class / controller; rendering is handled by the TUI layer.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)


@dataclass
class REPLConfig:
    """Configuration for the REPL screen."""
    commands: list[dict] = field(default_factory=list)
    initial_tools: list[Any] = field(default_factory=list)
    mcp_clients: list[Any] = field(default_factory=list)
    debug: bool = False
    system_prompt: Optional[str] = None
    append_system_prompt: Optional[str] = None
    disable_slash_commands: bool = False
    thinking_config: Optional[dict] = None
    direct_connect_config: Optional[dict] = None
    on_turn_complete: Optional[Callable] = None


@dataclass
class REPLState:
    """Mutable state for the REPL session."""
    messages: list[dict] = field(default_factory=list)
    is_loading: bool = False
    current_prompt: str = ""
    error: Optional[str] = None
    input_mode: str = "normal"  # 'normal' | 'vim' | 'paste'
    cost_usd: float = 0.0
    turn_count: int = 0


class REPLScreen:
    """Main REPL screen controller.

    Mirrors the REPL React component from REPL.tsx, but as a Python
    controller that drives the TUI output layer.
    """

    def __init__(self, config: REPLConfig) -> None:
        self._config = config
        self._state = REPLState()
        self._on_message_callbacks: list[Callable] = []

    @property
    def state(self) -> REPLState:
        return self._state

    def on_message(self, callback: Callable[[dict], None]) -> None:
        self._on_message_callbacks.append(callback)

    def submit_input(self, text: str) -> None:
        """Submit user input for processing."""
        self._state.current_prompt = text
        self._state.is_loading = True

    def append_message(self, message: dict) -> None:
        self._state.messages.append(message)
        for cb in self._on_message_callbacks:
            cb(message)

    def set_error(self, error: Optional[str]) -> None:
        self._state.error = error
        self._state.is_loading = False

    def clear(self) -> None:
        self._state.messages.clear()
        self._state.error = None
        self._state.current_prompt = ""

    def get_visible_messages(self) -> list[dict]:
        """Return messages for display (filters synthetic messages)."""
        return [
            m for m in self._state.messages
            if m.get("type") not in ("system",) or m.get("subtype") != "post_turn_summary"
        ]

    def get_cost_display(self) -> str:
        cost = self._state.cost_usd
        if cost < 0.01:
            return f"${cost:.4f}"
        return f"${cost:.3f}"

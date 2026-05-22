"""Keybinding manager backed by the mirrored keybindings package."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from ..keybindings.loadUserBindings import (
    getKeybindingsPath,
    loadKeybindingsSyncWithWarnings,
)
from ..keybindings.parser import KeybindingBlock, ParsedBinding, chordToDisplayString, parseBindings
from ..keybindings.reservedShortcuts import normalizeKeyForComparison
from ..types import Keybinding

logger = logging.getLogger(__name__)


def _binding_to_keybinding(binding: ParsedBinding) -> Keybinding:
    return Keybinding(
        key=chordToDisplayString(binding.chord),
        command=str(binding.action),
        description=str(binding.action),
        context=binding.context,
    )


DEFAULT_BINDINGS = [
    _binding_to_keybinding(binding)
    for binding in loadKeybindingsSyncWithWarnings()["bindings"]
]


class KeybindingManager:
    """Manage keybindings using the translated keybindings subsystem."""

    def __init__(self):
        self._handlers: dict[str, Callable] = {}
        self._bindings: dict[str, Keybinding] = {}
        self._warnings: list[dict] = []
        self._reload_from_package()

    def _reload_from_package(self) -> None:
        result = loadKeybindingsSyncWithWarnings()
        self._warnings = result["warnings"]
        bindings: dict[str, Keybinding] = {}
        for binding in result["bindings"]:
            display = chordToDisplayString(binding.chord)
            bindings[normalizeKeyForComparison(display)] = _binding_to_keybinding(binding)
        self._bindings = bindings

    def register(self, keybinding: Keybinding, handler: Optional[Callable] = None) -> None:
        self._bindings[normalizeKeyForComparison(keybinding.key)] = keybinding
        if handler is not None:
            self._handlers[keybinding.command] = handler

    def unregister(self, key: str) -> None:
        self._bindings.pop(normalizeKeyForComparison(key), None)

    def get(self, key: str) -> Optional[Keybinding]:
        return self._bindings.get(normalizeKeyForComparison(key))

    def get_handler(self, command: str) -> Optional[Callable]:
        return self._handlers.get(command)

    def get_all(self) -> list[Keybinding]:
        return list(self._bindings.values())

    def handle_key(self, key: str) -> bool:
        binding = self.get(key)
        if binding is None:
            return False
        handler = self._handlers.get(binding.command)
        if handler is None:
            return False
        try:
            handler()
            return True
        except Exception as exc:
            logger.error("Keybinding handler error: %s", exc)
            return False

    def load_user_bindings(self, path: Path) -> None:
        if path == Path(getKeybindingsPath()):
            self._reload_from_package()
            return
        try:
            if not path.exists():
                return
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            blocks = data.get("bindings") if isinstance(data, dict) else None
            if not isinstance(blocks, list):
                return
            parsed = parseBindings(
                [
                    KeybindingBlock(context=item["context"], bindings=dict(item["bindings"]))
                    for item in blocks
                    if isinstance(item, dict)
                    and isinstance(item.get("context"), str)
                    and isinstance(item.get("bindings"), dict)
                ]
            )
            for binding in parsed:
                keybinding = _binding_to_keybinding(binding)
                self._bindings[normalizeKeyForComparison(keybinding.key)] = keybinding
        except Exception as exc:
            logger.error("Failed to load keybindings: %s", exc)

    def format_bindings(self) -> str:
        self._reload_from_package()
        lines = ["Keybindings:", ""]
        bindings = sorted(self._bindings.values(), key=lambda binding: (binding.context, binding.key.lower()))
        current_context: str | None = None
        for binding in bindings:
            if binding.context != current_context:
                if current_context is not None:
                    lines.append("")
                current_context = binding.context
                lines.append(f"[{current_context}]")
            lines.append(f"  {binding.key:<20} {binding.command}")

        if self._warnings:
            lines.extend(["", f"Warnings: {len(self._warnings)}", "  Run /doctor for details."])

        return "\n".join(lines)

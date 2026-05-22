"""Sandbox permission request — focused port of src/components/permissions/SandboxPermissionRequest.tsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ...services.analytics.index import logEvent
from ...utils.sandbox.sandbox_adapter import shouldAllowManagedSandboxDomainsOnly
from ..CustomSelect import OptionWithDescription, Select
from .PermissionDialog import PermissionDialog


@dataclass
class SandboxPermissionRequest:
    hostPattern: dict[str, Any]
    onUserResponse: Callable[[dict[str, bool]], None]
    select: Select[str] = field(init=False)

    def __post_init__(self) -> None:
        host = str(self.hostPattern.get("host", ""))
        managed_domains_only = shouldAllowManagedSandboxDomainsOnly()
        options: list[OptionWithDescription[str]] = [
            OptionWithDescription(label="Yes", value="yes"),
        ]
        if not managed_domains_only:
            options.append(
                OptionWithDescription(
                    label=f"Yes, and don't ask again for {host}",
                    value="yes-dont-ask-again",
                )
            )
        options.append(
            OptionWithDescription(
                label="No, and tell vivian what to do differently (esc)",
                value="no",
            )
        )
        self.select = Select(options=options, onChange=self._on_select, onCancel=self._on_cancel)

    def _on_select(self, value: str) -> None:
        host = str(self.hostPattern.get("host", ""))
        logEvent("tengu_sandbox_network_dialog_result", {"host": host, "result": value})
        if value == "yes":
            self.onUserResponse({"allow": True, "persistToSettings": False})
        elif value == "yes-dont-ask-again":
            self.onUserResponse({"allow": True, "persistToSettings": True})
        else:
            self.onUserResponse({"allow": False, "persistToSettings": False})

    def _on_cancel(self) -> None:
        host = str(self.hostPattern.get("host", ""))
        logEvent("tengu_sandbox_network_dialog_result", {"host": host, "result": "cancel"})
        self.onUserResponse({"allow": False, "persistToSettings": False})

    def handleKeyDown(self, event: object) -> None:
        self.select.handleKeyDown(event)

    def render_lines(self) -> list[str]:
        host = str(self.hostPattern.get("host", ""))
        content = [
            f"Host: {host}",
            "Do you want to allow this connection?",
            "",
            *self.select.render_lines(),
        ]
        return PermissionDialog(title="Network request outside of sandbox", children=content).render_lines()


__all__ = ["SandboxPermissionRequest"]
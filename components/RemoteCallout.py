"""Remote callout — focused port of src/components/RemoteCallout.tsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal

from ..bridge.bridgeEnabled import isBridgeEnabled
from ..utils.auth import get_vivian_ai_oauth_tokens
from ..utils.config import get_global_config, save_global_config
from .CustomSelect import OptionWithDescription, Select
from .permissions import PermissionDialog


RemoteCalloutSelection = Literal["enable", "dismiss"]


@dataclass
class RemoteCallout:
    onDone: Callable[[RemoteCalloutSelection], None]
    select: Select[RemoteCalloutSelection] = field(init=False)

    def __post_init__(self) -> None:
        save_global_config(
            lambda current: current
            if current.get("remoteDialogSeen")
            else {**current, "remoteDialogSeen": True}
        )
        self.select = Select(
            options=[
                OptionWithDescription(
                    label="Enable Remote Control for this session",
                    description="Opens a secure connection to api-vivian.d0a.net.",
                    value="enable",
                ),
                OptionWithDescription(
                    label="Never mind",
                    description="You can always enable it later with /remote-control.",
                    value="dismiss",
                ),
            ],
            onChange=self._handle_select,
            onCancel=self._handle_cancel,
        )

    def _handle_cancel(self) -> None:
        self.onDone("dismiss")

    def _handle_select(self, value: RemoteCalloutSelection) -> None:
        self.onDone(value)

    def handleKeyDown(self, event: object) -> None:
        self.select.handleKeyDown(event)

    def render_lines(self) -> list[str]:
        content = [
            "Remote Control lets you access this CLI session from the web (api-vivian.d0a.net/code)",
            "or the vivian app, so you can pick up where you left off on any device.",
            "",
            "You can disconnect remote access anytime by running /remote-control again.",
            "",
        ]
        content.extend(self.select.render_lines())
        return PermissionDialog(title="Remote Control", children=content).render_lines()


def shouldShowRemoteCallout() -> bool:
    config = get_global_config()
    if config.get("remoteDialogSeen"):
        return False
    if not isBridgeEnabled():
        return False
    tokens = get_vivian_ai_oauth_tokens()
    if tokens is None or not getattr(tokens, "access_token", None):
        return False
    return True


__all__ = ["RemoteCallout", "RemoteCalloutSelection", "shouldShowRemoteCallout"]
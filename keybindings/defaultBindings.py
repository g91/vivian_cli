"""Default keybindings — mirrors src/keybindings/defaultBindings.ts."""
from __future__ import annotations

import os

from ..utils.platform import get_platform
from .parser import KeybindingBlock


def _env_truthy(name: str) -> bool:
    value = os.environ.get(name)
    if value is None:
        return False
    return value.strip().lower() not in {"", "0", "false", "no", "off"}


def _feature(name: str) -> bool:
    normalized = name.upper()
    aliases = {
        "KAIROS": ["KAIROS"],
        "KAIROS_BRIEF": ["KAIROS_BRIEF"],
        "QUICK_SEARCH": ["QUICK_SEARCH"],
        "TERMINAL_PANEL": ["TERMINAL_PANEL"],
        "MESSAGE_ACTIONS": ["MESSAGE_ACTIONS"],
        "VOICE_MODE": ["VOICE_MODE"],
    }
    for candidate in aliases.get(normalized, [normalized]):
        if _env_truthy(candidate):
            return True
    return False


IMAGE_PASTE_KEY = "alt+v" if get_platform() == "windows" else "ctrl+v"

# Python cannot infer the upstream Node/Bun VT-mode behavior exactly, so keep
# the portable shortcut except on Windows when explicitly disabled.
SUPPORTS_TERMINAL_VT_MODE = get_platform() != "windows" or not _env_truthy(
    "vivian_CODE_DISABLE_VT_MODE"
)
MODE_CYCLE_KEY = "shift+tab" if SUPPORTS_TERMINAL_VT_MODE else "meta+m"


DEFAULT_BINDINGS: list[KeybindingBlock] = [
    KeybindingBlock(
        context="Global",
        bindings={
            "ctrl+c": "app:interrupt",
            "ctrl+d": "app:exit",
            "ctrl+l": "app:redraw",
            "ctrl+t": "app:toggleTodos",
            "ctrl+o": "app:toggleTranscript",
            **(
                {"ctrl+shift+b": "app:toggleBrief"}
                if _feature("KAIROS") or _feature("KAIROS_BRIEF")
                else {}
            ),
            "ctrl+shift+o": "app:toggleTeammatePreview",
            "ctrl+r": "history:search",
            **(
                {
                    "ctrl+shift+f": "app:globalSearch",
                    "cmd+shift+f": "app:globalSearch",
                    "ctrl+shift+p": "app:quickOpen",
                    "cmd+shift+p": "app:quickOpen",
                }
                if _feature("QUICK_SEARCH")
                else {}
            ),
            **({"meta+j": "app:toggleTerminal"} if _feature("TERMINAL_PANEL") else {}),
        },
    ),
    KeybindingBlock(
        context="Chat",
        bindings={
            "escape": "chat:cancel",
            "ctrl+x ctrl+k": "chat:killAgents",
            MODE_CYCLE_KEY: "chat:cycleMode",
            "meta+p": "chat:modelPicker",
            "meta+o": "chat:fastMode",
            "meta+t": "chat:thinkingToggle",
            "enter": "chat:submit",
            "up": "history:previous",
            "down": "history:next",
            "ctrl+_": "chat:undo",
            "ctrl+shift+-": "chat:undo",
            "ctrl+x ctrl+e": "chat:externalEditor",
            "ctrl+g": "chat:externalEditor",
            "ctrl+s": "chat:stash",
            IMAGE_PASTE_KEY: "chat:imagePaste",
            **({"shift+up": "chat:messageActions"} if _feature("MESSAGE_ACTIONS") else {}),
            **({"space": "voice:pushToTalk"} if _feature("VOICE_MODE") else {}),
        },
    ),
    KeybindingBlock(
        context="Autocomplete",
        bindings={
            "tab": "autocomplete:accept",
            "escape": "autocomplete:dismiss",
            "up": "autocomplete:previous",
            "down": "autocomplete:next",
        },
    ),
    KeybindingBlock(
        context="Settings",
        bindings={
            "escape": "confirm:no",
            "up": "select:previous",
            "down": "select:next",
            "k": "select:previous",
            "j": "select:next",
            "ctrl+p": "select:previous",
            "ctrl+n": "select:next",
            "space": "select:accept",
            "enter": "settings:close",
            "/": "settings:search",
            "r": "settings:retry",
        },
    ),
    KeybindingBlock(
        context="Confirmation",
        bindings={
            "y": "confirm:yes",
            "n": "confirm:no",
            "enter": "confirm:yes",
            "escape": "confirm:no",
            "up": "confirm:previous",
            "down": "confirm:next",
            "tab": "confirm:nextField",
            "space": "confirm:toggle",
            "shift+tab": "confirm:cycleMode",
            "ctrl+e": "confirm:toggleExplanation",
            "ctrl+d": "permission:toggleDebug",
        },
    ),
    KeybindingBlock(
        context="Tabs",
        bindings={
            "tab": "tabs:next",
            "shift+tab": "tabs:previous",
            "right": "tabs:next",
            "left": "tabs:previous",
        },
    ),
    KeybindingBlock(
        context="Transcript",
        bindings={
            "ctrl+e": "transcript:toggleShowAll",
            "ctrl+c": "transcript:exit",
            "escape": "transcript:exit",
            "q": "transcript:exit",
        },
    ),
    KeybindingBlock(
        context="HistorySearch",
        bindings={
            "ctrl+r": "historySearch:next",
            "escape": "historySearch:accept",
            "tab": "historySearch:accept",
            "ctrl+c": "historySearch:cancel",
            "enter": "historySearch:execute",
        },
    ),
    KeybindingBlock(context="Task", bindings={"ctrl+b": "task:background"}),
    KeybindingBlock(
        context="ThemePicker",
        bindings={"ctrl+t": "theme:toggleSyntaxHighlighting"},
    ),
    KeybindingBlock(
        context="Scroll",
        bindings={
            "pageup": "scroll:pageUp",
            "pagedown": "scroll:pageDown",
            "wheelup": "scroll:lineUp",
            "wheeldown": "scroll:lineDown",
            "ctrl+home": "scroll:top",
            "ctrl+end": "scroll:bottom",
            "ctrl+shift+c": "selection:copy",
            "cmd+c": "selection:copy",
        },
    ),
    KeybindingBlock(context="Help", bindings={"escape": "help:dismiss"}),
    KeybindingBlock(
        context="Attachments",
        bindings={
            "right": "attachments:next",
            "left": "attachments:previous",
            "backspace": "attachments:remove",
            "delete": "attachments:remove",
            "down": "attachments:exit",
            "escape": "attachments:exit",
        },
    ),
    KeybindingBlock(
        context="Footer",
        bindings={
            "up": "footer:up",
            "ctrl+p": "footer:up",
            "down": "footer:down",
            "ctrl+n": "footer:down",
            "right": "footer:next",
            "left": "footer:previous",
            "enter": "footer:openSelected",
            "escape": "footer:clearSelection",
        },
    ),
    KeybindingBlock(
        context="MessageSelector",
        bindings={
            "up": "messageSelector:up",
            "down": "messageSelector:down",
            "k": "messageSelector:up",
            "j": "messageSelector:down",
            "ctrl+p": "messageSelector:up",
            "ctrl+n": "messageSelector:down",
            "ctrl+up": "messageSelector:top",
            "shift+up": "messageSelector:top",
            "meta+up": "messageSelector:top",
            "shift+k": "messageSelector:top",
            "ctrl+down": "messageSelector:bottom",
            "shift+down": "messageSelector:bottom",
            "meta+down": "messageSelector:bottom",
            "shift+j": "messageSelector:bottom",
            "enter": "messageSelector:select",
        },
    ),
] + (
    [
        KeybindingBlock(
            context="MessageActions",
            bindings={
                "up": "messageActions:prev",
                "down": "messageActions:next",
                "k": "messageActions:prev",
                "j": "messageActions:next",
                "meta+up": "messageActions:top",
                "meta+down": "messageActions:bottom",
                "super+up": "messageActions:top",
                "super+down": "messageActions:bottom",
                "shift+up": "messageActions:prevUser",
                "shift+down": "messageActions:nextUser",
                "escape": "messageActions:escape",
                "ctrl+c": "messageActions:ctrlc",
                "enter": "messageActions:enter",
                "c": "messageActions:c",
                "p": "messageActions:p",
            },
        )
    ]
    if _feature("MESSAGE_ACTIONS")
    else []
) + [
    KeybindingBlock(
        context="DiffDialog",
        bindings={
            "escape": "diff:dismiss",
            "left": "diff:previousSource",
            "right": "diff:nextSource",
            "up": "diff:previousFile",
            "down": "diff:nextFile",
            "enter": "diff:viewDetails",
        },
    ),
    KeybindingBlock(
        context="ModelPicker",
        bindings={
            "left": "modelPicker:decreaseEffort",
            "right": "modelPicker:increaseEffort",
        },
    ),
    KeybindingBlock(
        context="Select",
        bindings={
            "up": "select:previous",
            "down": "select:next",
            "j": "select:next",
            "k": "select:previous",
            "ctrl+n": "select:next",
            "ctrl+p": "select:previous",
            "enter": "select:accept",
            "escape": "select:cancel",
        },
    ),
    KeybindingBlock(
        context="Plugin",
        bindings={
            "space": "plugin:toggle",
            "i": "plugin:install",
        },
    ),
]


default_bindings = DEFAULT_BINDINGS
"""Text input types — mirrors src/types/textInputTypes.ts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Optional, Protocol, TypeAlias


@dataclass(frozen=True)
class InlineGhostText:
    text: str
    fullCommand: str
    insertPosition: int


class InputFilter(Protocol):
    def __call__(self, input_value: str, key: Any) -> str: ...


VimMode = Literal["INSERT", "NORMAL"]


@dataclass
class BaseTextInputProps:
    value: str
    onChange: Callable[[str], None]
    columns: int
    cursorOffset: int
    onChangeCursorOffset: Callable[[int], None]
    onHistoryUp: Optional[Callable[[], None]] = None
    onHistoryDown: Optional[Callable[[], None]] = None
    placeholder: Optional[str] = None
    multiline: bool = True
    focus: bool = True
    mask: Optional[str] = None
    showCursor: bool = False
    highlightPastedText: bool = False
    onSubmit: Optional[Callable[[str], None]] = None
    onExit: Optional[Callable[[], None]] = None
    onExitMessage: Optional[Callable[[bool, Optional[str]], None]] = None
    onHistoryReset: Optional[Callable[[], None]] = None
    onClearInput: Optional[Callable[[], None]] = None
    maxVisibleLines: Optional[int] = None
    onImagePaste: Optional[Callable[[str, Optional[str], Optional[str], Optional[Any], Optional[str]], None]] = None
    onPaste: Optional[Callable[[str], None]] = None
    onIsPastingChange: Optional[Callable[[bool], None]] = None
    disableCursorMovementForUpDownKeys: bool = False
    disableEscapeDoublePress: bool = False
    argumentHint: Optional[str] = None
    onUndo: Optional[Callable[[], None]] = None
    dimColor: bool = False
    highlights: list[Any] = field(default_factory=list)
    placeholderElement: Optional[Any] = None
    inlineGhostText: Optional[InlineGhostText] = None
    inputFilter: Optional[InputFilter] = None


@dataclass
class VimTextInputProps(BaseTextInputProps):
    initialMode: Optional[VimMode] = None
    onModeChange: Optional[Callable[[VimMode], None]] = None


@dataclass
class PasteState:
    chunks: list[str] = field(default_factory=list)
    timeoutId: Any = None


@dataclass
class BaseInputState:
    onInput: Callable[[str, Any], None]
    renderedValue: str
    offset: int
    setOffset: Callable[[int], None]
    cursorLine: int
    cursorColumn: int
    viewportCharOffset: int
    viewportCharEnd: int
    isPasting: Optional[bool] = None
    pasteState: Optional[PasteState] = None


TextInputState = BaseInputState


@dataclass
class VimInputState(BaseInputState):
    mode: VimMode = "INSERT"
    setMode: Callable[[VimMode], None] = lambda _mode: None


PromptInputMode = Literal["bash", "prompt", "orphaned-permission", "task-notification"]
EditablePromptInputMode = Literal["bash", "prompt", "orphaned-permission"]
QueuePriority = Literal["now", "next", "later"]


@dataclass
class OrphanedPermission:
    permissionResult: Any
    assistantMessage: Any


@dataclass
class QueuedCommand:
    value: str | list[Any]
    mode: PromptInputMode
    priority: Optional[QueuePriority] = None
    uuid: Optional[str] = None
    orphanedPermission: Optional[OrphanedPermission] = None
    pastedContents: Optional[dict[int, Any]] = None
    preExpansionValue: Optional[str] = None
    skipSlashCommands: Optional[bool] = None
    bridgeOrigin: Optional[bool] = None
    isMeta: Optional[bool] = None
    origin: Optional[Any] = None
    workload: Optional[str] = None
    agentId: Optional[str] = None


def isValidImagePaste(c: Any) -> bool:
    data = getattr(c, "data", None) if not isinstance(c, dict) else c.get("data")
    if isinstance(data, str):
        return data != ""
    base64_data = getattr(c, "base64", None) if not isinstance(c, dict) else c.get("base64")
    return isinstance(base64_data, str) and base64_data != ""


def getImagePasteIds(pastedContents: Optional[dict[int, Any]]) -> Optional[list[int]]:
    if not pastedContents:
        return None
    image_ids = [paste_id for paste_id, content in pastedContents.items() if isValidImagePaste(content)]
    return image_ids or None


inline_ghost_text = InlineGhostText
base_text_input_props = BaseTextInputProps
vim_text_input_props = VimTextInputProps
base_input_state = BaseInputState
text_input_state = TextInputState
vim_input_state = VimInputState
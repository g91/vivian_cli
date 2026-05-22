"""Type definitions for commands — mirrors src/types/command.ts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal, Optional, Protocol, TypeAlias


@dataclass(init=False)
class TextResult:
    type: Literal["text"] = "text"
    value: str = ""

    def __init__(self, value: str = "", *, type: Literal["text"] = "text") -> None:
        self.type = type
        self.value = value


@dataclass
class CompactResult:
    type: Literal["compact"] = "compact"
    compactionResult: Any = None
    displayText: Optional[str] = None

    @property
    def compaction_result(self) -> Any:
        return self.compactionResult

    @property
    def display_text(self) -> Optional[str]:
        return self.displayText


@dataclass
class SkipResult:
    type: Literal["skip"] = "skip"


LocalCommandResult: TypeAlias = TextResult | CompactResult | SkipResult


class LocalJSXCommandOnDone(Protocol):
    def __call__(self, result: Optional[str] = None, options: Optional[dict[str, Any]] = None) -> None: ...


LocalCommandCall: TypeAlias = Callable[[str, Any], Any]
LocalJSXCommandCall: TypeAlias = Callable[[LocalJSXCommandOnDone, Any, str], Any]


@dataclass
class LocalCommandModule:
    call: LocalCommandCall


@dataclass
class LocalJSXCommandModule:
    call: LocalJSXCommandCall


class PromptCommand:
    type: Literal["prompt"] = "prompt"
    progressMessage: str
    contentLength: int
    argNames: Optional[list[str]]
    allowedTools: Optional[list[str]]
    model: Optional[str]
    source: str
    pluginInfo: Optional[dict[str, Any]]
    disableNonInteractive: Optional[bool]
    hooks: Optional[dict[str, Any]]
    skillRoot: Optional[str]
    context: Literal["inline", "fork"]
    agent: Optional[str]
    effort: Optional[str]
    paths: Optional[list[str]]
    getPromptForCommand: Optional[Callable[[str, Any], Any]]

    def __init__(
        self,
        *,
        type: Literal["prompt"] = "prompt",
        progressMessage: str = "",
        contentLength: int = 0,
        argNames: Optional[list[str]] = None,
        allowedTools: Optional[list[str]] = None,
        model: Optional[str] = None,
        source: str = "builtin",
        pluginInfo: Optional[dict[str, Any]] = None,
        disableNonInteractive: Optional[bool] = None,
        hooks: Optional[dict[str, Any]] = None,
        skillRoot: Optional[str] = None,
        context: Literal["inline", "fork"] = "inline",
        agent: Optional[str] = None,
        effort: Optional[str] = None,
        paths: Optional[list[str]] = None,
        getPromptForCommand: Optional[Callable[[str, Any], Any]] = None,
        progress_message: Optional[str] = None,
        content_length: Optional[int] = None,
        arg_names: Optional[list[str]] = None,
        allowed_tools: Optional[list[str]] = None,
        plugin_info: Optional[dict[str, Any]] = None,
        disable_non_interactive: Optional[bool] = None,
        skill_root: Optional[str] = None,
        get_prompt_for_command: Optional[Callable[[str, Any], Any]] = None,
    ) -> None:
        self.type = type
        self.progressMessage = progressMessage if progress_message is None else progress_message
        self.contentLength = contentLength if content_length is None else content_length
        self.argNames = argNames if arg_names is None else arg_names
        self.allowedTools = allowedTools if allowed_tools is None else allowed_tools
        self.model = model
        self.source = source
        self.pluginInfo = pluginInfo if plugin_info is None else plugin_info
        self.disableNonInteractive = (
            disableNonInteractive if disable_non_interactive is None else disable_non_interactive
        )
        self.hooks = hooks
        self.skillRoot = skillRoot if skill_root is None else skill_root
        self.context = context
        self.agent = agent
        self.effort = effort
        self.paths = paths
        self.getPromptForCommand = (
            getPromptForCommand if get_prompt_for_command is None else get_prompt_for_command
        )

    @property
    def progress_message(self) -> str:
        return self.progressMessage

    @property
    def content_length(self) -> int:
        return self.contentLength

    @property
    def arg_names(self) -> Optional[list[str]]:
        return self.argNames

    @property
    def allowed_tools(self) -> Optional[list[str]]:
        return self.allowedTools

    @property
    def plugin_info(self) -> Optional[dict[str, Any]]:
        return self.pluginInfo

    @property
    def disable_non_interactive(self) -> Optional[bool]:
        return self.disableNonInteractive

    @property
    def skill_root(self) -> Optional[str]:
        return self.skillRoot

    @property
    def get_prompt_for_command(self) -> Optional[Callable[[str, Any], Any]]:
        return self.getPromptForCommand


CommandResultDisplay = Literal["skip", "system", "user"]
ResumeEntrypoint = Literal[
    "cli_flag",
    "slash_command_picker",
    "slash_command_session_id",
    "slash_command_title",
    "fork",
]
CommandAvailability = Literal["vivian-ai", "console"]


@dataclass
class LocalCommand:
    type: Literal["local"] = "local"
    supportsNonInteractive: bool = True
    load: Optional[Callable[[], Any]] = None


@dataclass
class LocalJSXCommand:
    type: Literal["local-jsx"] = "local-jsx"
    load: Optional[Callable[[], Any]] = None


@dataclass
class CommandBase:
    description: str
    name: str
    availability: Optional[list[CommandAvailability]] = None
    hasUserSpecifiedDescription: Optional[bool] = None
    isEnabled: Optional[Callable[[], bool]] = None
    isHidden: Optional[bool] = None
    aliases: Optional[list[str]] = None
    isMcp: Optional[bool] = None
    argumentHint: Optional[str] = None
    whenToUse: Optional[str] = None
    version: Optional[str] = None
    disableModelInvocation: Optional[bool] = None
    userInvocable: Optional[bool] = None
    loadedFrom: Optional[str] = None
    kind: Optional[Literal["workflow"]] = None
    immediate: Optional[bool] = None
    isSensitive: Optional[bool] = None
    userFacingName: Optional[Callable[[], str]] = None


Command: TypeAlias = CommandBase | PromptCommand | LocalCommand | LocalJSXCommand


def getCommandName(cmd: Any) -> str:
    resolver = getattr(cmd, "userFacingName", None)
    if callable(resolver):
        return resolver()
    return getattr(cmd, "name")


def isCommandEnabled(cmd: Any) -> bool:
    resolver = getattr(cmd, "isEnabled", None)
    return resolver() if callable(resolver) else True

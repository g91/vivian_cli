"""Log/session message types — mirrors src/types/logs.ts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Optional, TypeAlias


@dataclass
class SerializedMessage:
    cwd: str
    userType: str
    sessionId: str
    timestamp: str
    version: str
    type: str = "user"
    entrypoint: Optional[str] = None
    gitBranch: Optional[str] = None
    slug: Optional[str] = None
    message: Any = None

    @property
    def user_type(self) -> str:
        return self.userType

    @property
    def session_id(self) -> str:
        return self.sessionId

    @property
    def git_branch(self) -> Optional[str]:
        return self.gitBranch


@dataclass
class LogOption:
    date: str
    messages: list[SerializedMessage]
    value: int
    created: datetime
    modified: datetime
    firstPrompt: str
    messageCount: int
    fullPath: Optional[str] = None
    fileSize: Optional[int] = None
    isSidechain: bool = False
    isLite: bool = False
    sessionId: Optional[str] = None
    teamName: Optional[str] = None
    agentName: Optional[str] = None
    agentColor: Optional[str] = None
    agentSetting: Optional[str] = None
    isTeammate: bool = False
    leafUuid: Optional[str] = None
    summary: Optional[str] = None
    customTitle: Optional[str] = None
    tag: Optional[str] = None
    gitBranch: Optional[str] = None
    projectPath: Optional[str] = None
    prNumber: Optional[int] = None
    prUrl: Optional[str] = None
    prRepository: Optional[str] = None
    mode: Optional[str] = None
    fileHistorySnapshots: Optional[list[Any]] = None
    attributionSnapshots: Optional[list[Any]] = None
    contextCollapseCommits: Optional[list[Any]] = None
    contextCollapseSnapshot: Optional[Any] = None
    worktreeSession: Optional[Any] = None
    contentReplacements: Optional[list[Any]] = None

    @property
    def first_prompt(self) -> str:
        return self.firstPrompt

    @property
    def message_count(self) -> int:
        return self.messageCount

    @property
    def full_path(self) -> Optional[str]:
        return self.fullPath

    @property
    def file_size(self) -> Optional[int]:
        return self.fileSize

    @property
    def is_sidechain(self) -> bool:
        return self.isSidechain

    @property
    def is_lite(self) -> bool:
        return self.isLite

    @property
    def session_id(self) -> Optional[str]:
        return self.sessionId

    @property
    def team_name(self) -> Optional[str]:
        return self.teamName

    @property
    def agent_name(self) -> Optional[str]:
        return self.agentName

    @property
    def agent_color(self) -> Optional[str]:
        return self.agentColor

    @property
    def agent_setting(self) -> Optional[str]:
        return self.agentSetting

    @property
    def is_teammate(self) -> bool:
        return self.isTeammate

    @property
    def leaf_uuid(self) -> Optional[str]:
        return self.leafUuid

    @property
    def custom_title(self) -> Optional[str]:
        return self.customTitle

    @property
    def git_branch(self) -> Optional[str]:
        return self.gitBranch

    @property
    def project_path(self) -> Optional[str]:
        return self.projectPath

    @property
    def pr_number(self) -> Optional[int]:
        return self.prNumber

    @property
    def pr_url(self) -> Optional[str]:
        return self.prUrl

    @property
    def pr_repository(self) -> Optional[str]:
        return self.prRepository


@dataclass
class SummaryMessage:
    type: Literal["summary"] = "summary"
    leafUuid: str = ""
    summary: str = ""

    @property
    def leaf_uuid(self) -> str:
        return self.leafUuid


@dataclass
class CustomTitleMessage:
    type: Literal["custom-title"] = "custom-title"
    sessionId: str = ""
    customTitle: str = ""

    @property
    def session_id(self) -> str:
        return self.sessionId

    @property
    def custom_title(self) -> str:
        return self.customTitle


@dataclass
class AiTitleMessage:
    type: Literal["ai-title"] = "ai-title"
    sessionId: str = ""
    aiTitle: str = ""

    @property
    def session_id(self) -> str:
        return self.sessionId

    @property
    def ai_title(self) -> str:
        return self.aiTitle


@dataclass
class LastPromptMessage:
    type: Literal["last-prompt"] = "last-prompt"
    sessionId: str = ""
    lastPrompt: str = ""


@dataclass
class TaskSummaryMessage:
    type: Literal["task-summary"] = "task-summary"
    sessionId: str = ""
    summary: str = ""
    timestamp: str = ""


@dataclass
class TagMessage:
    type: Literal["tag"] = "tag"
    sessionId: str = ""
    tag: str = ""


@dataclass
class AgentNameMessage:
    type: Literal["agent-name"] = "agent-name"
    sessionId: str = ""
    agentName: str = ""


@dataclass
class AgentColorMessage:
    type: Literal["agent-color"] = "agent-color"
    sessionId: str = ""
    agentColor: str = ""


@dataclass
class AgentSettingMessage:
    type: Literal["agent-setting"] = "agent-setting"
    sessionId: str = ""
    agentSetting: str = ""


@dataclass
class PRLinkMessage:
    type: Literal["pr-link"] = "pr-link"
    sessionId: str = ""
    prNumber: int = 0
    prUrl: str = ""
    prRepository: str = ""
    timestamp: str = ""


Entry: TypeAlias = (
    SerializedMessage
    | SummaryMessage
    | CustomTitleMessage
    | AiTitleMessage
    | LastPromptMessage
    | TaskSummaryMessage
    | TagMessage
    | AgentNameMessage
    | AgentColorMessage
    | AgentSettingMessage
    | PRLinkMessage
)


def sortLogs(logs: list[LogOption]) -> list[LogOption]:
    return sorted(logs, key=lambda log: (log.modified, log.created), reverse=True)

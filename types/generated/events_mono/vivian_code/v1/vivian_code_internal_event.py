"""Generated from events_mono/vivian_code/v1/vivian_code_internal_event.proto."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from ....google.protobuf.timestamp import Timestamp
from ...common.v1.auth import PublicApiAuth


def isSet(value: Any) -> bool:
    return value is not None


def fromTimestamp(t: Timestamp) -> datetime:
    return datetime.fromtimestamp(t.seconds + (t.nanos / 1_000_000_000))


def fromJsonTimestamp(o: Any) -> datetime:
    if isinstance(o, datetime):
        return o
    if isinstance(o, str):
        return datetime.fromisoformat(o.replace("Z", "+00:00"))
    return fromTimestamp(Timestamp.fromJSON(o))


@dataclass
class GitHubActionsMetadata:
    actor_id: str = ""
    repository_id: str = ""
    repository_owner_id: str = ""

    @classmethod
    def fromJSON(cls, object: Any) -> "GitHubActionsMetadata":
        return cls(
            actor_id=str(object.get("actor_id", "")) if isSet(object.get("actor_id")) else "",
            repository_id=str(object.get("repository_id", "")) if isSet(object.get("repository_id")) else "",
            repository_owner_id=str(object.get("repository_owner_id", "")) if isSet(object.get("repository_owner_id")) else "",
        )

    @staticmethod
    def toJSON(message: "GitHubActionsMetadata") -> dict[str, Any]:
        return {
            "actor_id": message.actor_id,
            "repository_id": message.repository_id,
            "repository_owner_id": message.repository_owner_id,
        }

    @classmethod
    def create(cls, base: Optional[dict[str, Any]] = None) -> "GitHubActionsMetadata":
        return cls.fromPartial(base or {})

    @classmethod
    def fromPartial(cls, object: Any) -> "GitHubActionsMetadata":
        data = object if isinstance(object, dict) else vars(object)
        return cls(
            actor_id=data.get("actor_id", "") or "",
            repository_id=data.get("repository_id", "") or "",
            repository_owner_id=data.get("repository_owner_id", "") or "",
        )


@dataclass
class EnvironmentMetadata:
    platform: str = ""
    node_version: str = ""
    terminal: str = ""
    package_managers: str = ""
    runtimes: str = ""
    is_running_with_bun: bool = False
    is_ci: bool = False
    is_claubbit: bool = False
    is_github_action: bool = False
    is_vivian_code_action: bool = False
    is_vivian_ai_auth: bool = False
    version: str = ""
    github_event_name: str = ""
    github_actions_runner_environment: str = ""
    github_actions_runner_os: str = ""
    github_action_ref: str = ""
    wsl_version: str = ""
    github_actions_metadata: Optional[GitHubActionsMetadata] = None
    arch: str = ""
    is_vivian_code_remote: bool = False
    remote_environment_type: str = ""
    vivian_code_container_id: str = ""
    vivian_code_remote_session_id: str = ""
    tags: list[str] = field(default_factory=list)
    deployment_environment: str = ""
    is_conductor: bool = False
    version_base: str = ""
    coworker_type: str = ""
    build_time: str = ""
    is_local_agent_mode: bool = False
    linux_distro_id: str = ""
    linux_distro_version: str = ""
    linux_kernel: str = ""
    vcs: str = ""
    platform_raw: str = ""

    @classmethod
    def fromJSON(cls, object: Any) -> "EnvironmentMetadata":
        data = object or {}
        return cls(
            platform=str(data.get("platform", "")) if isSet(data.get("platform")) else "",
            node_version=str(data.get("node_version", "")) if isSet(data.get("node_version")) else "",
            terminal=str(data.get("terminal", "")) if isSet(data.get("terminal")) else "",
            package_managers=str(data.get("package_managers", "")) if isSet(data.get("package_managers")) else "",
            runtimes=str(data.get("runtimes", "")) if isSet(data.get("runtimes")) else "",
            is_running_with_bun=bool(data.get("is_running_with_bun", False)),
            is_ci=bool(data.get("is_ci", False)),
            is_claubbit=bool(data.get("is_claubbit", False)),
            is_github_action=bool(data.get("is_github_action", False)),
            is_vivian_code_action=bool(data.get("is_vivian_code_action", False)),
            is_vivian_ai_auth=bool(data.get("is_vivian_ai_auth", False)),
            version=str(data.get("version", "")) if isSet(data.get("version")) else "",
            github_event_name=str(data.get("github_event_name", "")) if isSet(data.get("github_event_name")) else "",
            github_actions_runner_environment=str(data.get("github_actions_runner_environment", "")) if isSet(data.get("github_actions_runner_environment")) else "",
            github_actions_runner_os=str(data.get("github_actions_runner_os", "")) if isSet(data.get("github_actions_runner_os")) else "",
            github_action_ref=str(data.get("github_action_ref", "")) if isSet(data.get("github_action_ref")) else "",
            wsl_version=str(data.get("wsl_version", "")) if isSet(data.get("wsl_version")) else "",
            github_actions_metadata=GitHubActionsMetadata.fromJSON(data.get("github_actions_metadata")) if isSet(data.get("github_actions_metadata")) else None,
            arch=str(data.get("arch", "")) if isSet(data.get("arch")) else "",
            is_vivian_code_remote=bool(data.get("is_vivian_code_remote", False)),
            remote_environment_type=str(data.get("remote_environment_type", "")) if isSet(data.get("remote_environment_type")) else "",
            vivian_code_container_id=str(data.get("vivian_code_container_id", "")) if isSet(data.get("vivian_code_container_id")) else "",
            vivian_code_remote_session_id=str(data.get("vivian_code_remote_session_id", "")) if isSet(data.get("vivian_code_remote_session_id")) else "",
            tags=[str(item) for item in data.get("tags", [])],
            deployment_environment=str(data.get("deployment_environment", "")) if isSet(data.get("deployment_environment")) else "",
            is_conductor=bool(data.get("is_conductor", False)),
            version_base=str(data.get("version_base", "")) if isSet(data.get("version_base")) else "",
            coworker_type=str(data.get("coworker_type", "")) if isSet(data.get("coworker_type")) else "",
            build_time=str(data.get("build_time", "")) if isSet(data.get("build_time")) else "",
            is_local_agent_mode=bool(data.get("is_local_agent_mode", False)),
            linux_distro_id=str(data.get("linux_distro_id", "")) if isSet(data.get("linux_distro_id")) else "",
            linux_distro_version=str(data.get("linux_distro_version", "")) if isSet(data.get("linux_distro_version")) else "",
            linux_kernel=str(data.get("linux_kernel", "")) if isSet(data.get("linux_kernel")) else "",
            vcs=str(data.get("vcs", "")) if isSet(data.get("vcs")) else "",
            platform_raw=str(data.get("platform_raw", "")) if isSet(data.get("platform_raw")) else "",
        )

    @staticmethod
    def toJSON(message: "EnvironmentMetadata") -> dict[str, Any]:
        obj = dict(vars(message))
        if message.github_actions_metadata is not None:
            obj["github_actions_metadata"] = GitHubActionsMetadata.toJSON(message.github_actions_metadata)
        return obj

    @classmethod
    def create(cls, base: Optional[dict[str, Any]] = None) -> "EnvironmentMetadata":
        return cls.fromPartial(base or {})

    @classmethod
    def fromPartial(cls, object: Any) -> "EnvironmentMetadata":
        data = object if isinstance(object, dict) else vars(object)
        metadata = data.get("github_actions_metadata")
        return cls(
            platform=data.get("platform", "") or "",
            node_version=data.get("node_version", "") or "",
            terminal=data.get("terminal", "") or "",
            package_managers=data.get("package_managers", "") or "",
            runtimes=data.get("runtimes", "") or "",
            is_running_with_bun=bool(data.get("is_running_with_bun", False)),
            is_ci=bool(data.get("is_ci", False)),
            is_claubbit=bool(data.get("is_claubbit", False)),
            is_github_action=bool(data.get("is_github_action", False)),
            is_vivian_code_action=bool(data.get("is_vivian_code_action", False)),
            is_vivian_ai_auth=bool(data.get("is_vivian_ai_auth", False)),
            version=data.get("version", "") or "",
            github_event_name=data.get("github_event_name", "") or "",
            github_actions_runner_environment=data.get("github_actions_runner_environment", "") or "",
            github_actions_runner_os=data.get("github_actions_runner_os", "") or "",
            github_action_ref=data.get("github_action_ref", "") or "",
            wsl_version=data.get("wsl_version", "") or "",
            github_actions_metadata=GitHubActionsMetadata.fromPartial(metadata) if metadata is not None else None,
            arch=data.get("arch", "") or "",
            is_vivian_code_remote=bool(data.get("is_vivian_code_remote", False)),
            remote_environment_type=data.get("remote_environment_type", "") or "",
            vivian_code_container_id=data.get("vivian_code_container_id", "") or "",
            vivian_code_remote_session_id=data.get("vivian_code_remote_session_id", "") or "",
            tags=list(data.get("tags", []) or []),
            deployment_environment=data.get("deployment_environment", "") or "",
            is_conductor=bool(data.get("is_conductor", False)),
            version_base=data.get("version_base", "") or "",
            coworker_type=data.get("coworker_type", "") or "",
            build_time=data.get("build_time", "") or "",
            is_local_agent_mode=bool(data.get("is_local_agent_mode", False)),
            linux_distro_id=data.get("linux_distro_id", "") or "",
            linux_distro_version=data.get("linux_distro_version", "") or "",
            linux_kernel=data.get("linux_kernel", "") or "",
            vcs=data.get("vcs", "") or "",
            platform_raw=data.get("platform_raw", "") or "",
        )


@dataclass
class SlackContext:
    slack_team_id: str = ""
    is_enterprise_install: bool = False
    trigger: str = ""
    creation_method: str = ""

    @classmethod
    def fromJSON(cls, object: Any) -> "SlackContext":
        data = object or {}
        return cls(
            slack_team_id=str(data.get("slack_team_id", "")) if isSet(data.get("slack_team_id")) else "",
            is_enterprise_install=bool(data.get("is_enterprise_install", False)),
            trigger=str(data.get("trigger", "")) if isSet(data.get("trigger")) else "",
            creation_method=str(data.get("creation_method", "")) if isSet(data.get("creation_method")) else "",
        )

    @staticmethod
    def toJSON(message: "SlackContext") -> dict[str, Any]:
        return dict(vars(message))

    @classmethod
    def create(cls, base: Optional[dict[str, Any]] = None) -> "SlackContext":
        return cls.fromPartial(base or {})

    @classmethod
    def fromPartial(cls, object: Any) -> "SlackContext":
        data = object if isinstance(object, dict) else vars(object)
        return cls(
            slack_team_id=data.get("slack_team_id", "") or "",
            is_enterprise_install=bool(data.get("is_enterprise_install", False)),
            trigger=data.get("trigger", "") or "",
            creation_method=data.get("creation_method", "") or "",
        )


@dataclass
class vivianCodeInternalEvent:
    event_name: str = ""
    client_timestamp: Optional[datetime] = None
    model: str = ""
    session_id: str = ""
    user_type: str = ""
    betas: str = ""
    env: Optional[EnvironmentMetadata] = None
    entrypoint: str = ""
    agent_sdk_version: str = ""
    is_interactive: bool = False
    client_type: str = ""
    process: str = ""
    additional_metadata: str = ""
    auth: Optional[PublicApiAuth] = None
    server_timestamp: Optional[datetime] = None
    event_id: str = ""
    device_id: str = ""
    swe_bench_run_id: str = ""
    swe_bench_instance_id: str = ""
    swe_bench_task_id: str = ""
    email: str = ""
    agent_id: str = ""
    parent_session_id: str = ""
    agent_type: str = ""
    slack: Optional[SlackContext] = None
    team_name: str = ""
    skill_name: str = ""
    plugin_name: str = ""
    marketplace_name: str = ""

    @classmethod
    def fromJSON(cls, object: Any) -> "vivianCodeInternalEvent":
        data = object or {}
        return cls(
            event_name=str(data.get("event_name", "")) if isSet(data.get("event_name")) else "",
            client_timestamp=fromJsonTimestamp(data.get("client_timestamp")) if isSet(data.get("client_timestamp")) else None,
            model=str(data.get("model", "")) if isSet(data.get("model")) else "",
            session_id=str(data.get("session_id", "")) if isSet(data.get("session_id")) else "",
            user_type=str(data.get("user_type", "")) if isSet(data.get("user_type")) else "",
            betas=str(data.get("betas", "")) if isSet(data.get("betas")) else "",
            env=EnvironmentMetadata.fromJSON(data.get("env")) if isSet(data.get("env")) else None,
            entrypoint=str(data.get("entrypoint", "")) if isSet(data.get("entrypoint")) else "",
            agent_sdk_version=str(data.get("agent_sdk_version", "")) if isSet(data.get("agent_sdk_version")) else "",
            is_interactive=bool(data.get("is_interactive", False)),
            client_type=str(data.get("client_type", "")) if isSet(data.get("client_type")) else "",
            process=str(data.get("process", "")) if isSet(data.get("process")) else "",
            additional_metadata=str(data.get("additional_metadata", "")) if isSet(data.get("additional_metadata")) else "",
            auth=PublicApiAuth.fromJSON(data.get("auth")) if isSet(data.get("auth")) else None,
            server_timestamp=fromJsonTimestamp(data.get("server_timestamp")) if isSet(data.get("server_timestamp")) else None,
            event_id=str(data.get("event_id", "")) if isSet(data.get("event_id")) else "",
            device_id=str(data.get("device_id", "")) if isSet(data.get("device_id")) else "",
            swe_bench_run_id=str(data.get("swe_bench_run_id", "")) if isSet(data.get("swe_bench_run_id")) else "",
            swe_bench_instance_id=str(data.get("swe_bench_instance_id", "")) if isSet(data.get("swe_bench_instance_id")) else "",
            swe_bench_task_id=str(data.get("swe_bench_task_id", "")) if isSet(data.get("swe_bench_task_id")) else "",
            email=str(data.get("email", "")) if isSet(data.get("email")) else "",
            agent_id=str(data.get("agent_id", "")) if isSet(data.get("agent_id")) else "",
            parent_session_id=str(data.get("parent_session_id", "")) if isSet(data.get("parent_session_id")) else "",
            agent_type=str(data.get("agent_type", "")) if isSet(data.get("agent_type")) else "",
            slack=SlackContext.fromJSON(data.get("slack")) if isSet(data.get("slack")) else None,
            team_name=str(data.get("team_name", "")) if isSet(data.get("team_name")) else "",
            skill_name=str(data.get("skill_name", "")) if isSet(data.get("skill_name")) else "",
            plugin_name=str(data.get("plugin_name", "")) if isSet(data.get("plugin_name")) else "",
            marketplace_name=str(data.get("marketplace_name", "")) if isSet(data.get("marketplace_name")) else "",
        )

    @staticmethod
    def toJSON(message: "vivianCodeInternalEvent") -> dict[str, Any]:
        obj = dict(vars(message))
        if message.client_timestamp is not None:
            obj["client_timestamp"] = message.client_timestamp.isoformat().replace("+00:00", "Z")
        if message.server_timestamp is not None:
            obj["server_timestamp"] = message.server_timestamp.isoformat().replace("+00:00", "Z")
        if message.env is not None:
            obj["env"] = EnvironmentMetadata.toJSON(message.env)
        if message.auth is not None:
            obj["auth"] = PublicApiAuth.toJSON(message.auth)
        if message.slack is not None:
            obj["slack"] = SlackContext.toJSON(message.slack)
        return obj

    @classmethod
    def create(cls, base: Optional[dict[str, Any]] = None) -> "vivianCodeInternalEvent":
        return cls.fromPartial(base or {})

    @classmethod
    def fromPartial(cls, object: Any) -> "vivianCodeInternalEvent":
        data = object if isinstance(object, dict) else vars(object)
        env = data.get("env")
        auth = data.get("auth")
        slack = data.get("slack")
        return cls(
            event_name=data.get("event_name", "") or "",
            client_timestamp=data.get("client_timestamp"),
            model=data.get("model", "") or "",
            session_id=data.get("session_id", "") or "",
            user_type=data.get("user_type", "") or "",
            betas=data.get("betas", "") or "",
            env=EnvironmentMetadata.fromPartial(env) if env is not None else None,
            entrypoint=data.get("entrypoint", "") or "",
            agent_sdk_version=data.get("agent_sdk_version", "") or "",
            is_interactive=bool(data.get("is_interactive", False)),
            client_type=data.get("client_type", "") or "",
            process=data.get("process", "") or "",
            additional_metadata=data.get("additional_metadata", "") or "",
            auth=PublicApiAuth.fromPartial(auth) if auth is not None else None,
            server_timestamp=data.get("server_timestamp"),
            event_id=data.get("event_id", "") or "",
            device_id=data.get("device_id", "") or "",
            swe_bench_run_id=data.get("swe_bench_run_id", "") or "",
            swe_bench_instance_id=data.get("swe_bench_instance_id", "") or "",
            swe_bench_task_id=data.get("swe_bench_task_id", "") or "",
            email=data.get("email", "") or "",
            agent_id=data.get("agent_id", "") or "",
            parent_session_id=data.get("parent_session_id", "") or "",
            agent_type=data.get("agent_type", "") or "",
            slack=SlackContext.fromPartial(slack) if slack is not None else None,
            team_name=data.get("team_name", "") or "",
            skill_name=data.get("skill_name", "") or "",
            plugin_name=data.get("plugin_name", "") or "",
            marketplace_name=data.get("marketplace_name", "") or "",
        )


def createBaseGitHubActionsMetadata() -> GitHubActionsMetadata:
    return GitHubActionsMetadata()


def createBaseEnvironmentMetadata() -> EnvironmentMetadata:
    return EnvironmentMetadata()


def createBaseSlackContext() -> SlackContext:
    return SlackContext()


def createBasevivianCodeInternalEvent() -> vivianCodeInternalEvent:
    return vivianCodeInternalEvent()
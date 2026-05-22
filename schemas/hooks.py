"""Hook schemas — mirrors src/schemas/hooks.ts.

Hook-related schema definitions.  Extracted to break import cycles between
settings/types and plugins/schemas.

Both modules import from this shared location.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Union

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HOOK_EVENTS = (
    "PreToolUse",
    "PostToolUse",
    "UserPromptSubmit",
    "Notification",
    "Stop",
    "SubagentStop",
    "PreCompact",
)

SHELL_TYPES = ("bash", "powershell")

# ---------------------------------------------------------------------------
# Hook schemas (dataclasses mirror the Zod discriminated union)
# ---------------------------------------------------------------------------

@dataclass
class BashCommandHookSchema:
    """Shell command hook (type='command')."""
    type: Literal["command"] = "command"
    command: str = ""
    if_: Optional[str] = None          # permission-rule syntax filter
    shell: Optional[str] = None        # 'bash' | 'powershell'
    timeout: Optional[float] = None    # seconds
    status_message: Optional[str] = None
    once: bool = False
    async_: bool = False
    async_rewake: bool = False


@dataclass
class PromptHookSchema:
    """LLM prompt hook (type='prompt')."""
    type: Literal["prompt"] = "prompt"
    prompt: str = ""
    if_: Optional[str] = None
    timeout: Optional[float] = None
    model: Optional[str] = None
    status_message: Optional[str] = None
    once: bool = False


@dataclass
class HttpHookSchema:
    """HTTP hook (type='http')."""
    type: Literal["http"] = "http"
    url: str = ""
    if_: Optional[str] = None
    timeout: Optional[float] = None
    headers: Optional[dict[str, str]] = None
    allowed_env_vars: Optional[list[str]] = None
    status_message: Optional[str] = None
    once: bool = False


@dataclass
class AgentHookSchema:
    """Agentic verifier hook (type='agent')."""
    type: Literal["agent"] = "agent"
    prompt: str = ""
    if_: Optional[str] = None
    timeout: Optional[float] = None
    model: Optional[str] = None
    status_message: Optional[str] = None
    once: bool = False


# Union type for all hook command types
HookCommand = Union[
    BashCommandHookSchema,
    PromptHookSchema,
    HttpHookSchema,
    AgentHookSchema,
]


@dataclass
class HookMatcherSchema:
    """Matcher configuration with multiple hooks."""
    matcher: Optional[str] = None  # e.g. 'Write', 'Bash'
    hooks: list[HookCommand] = field(default_factory=list)


# Full hooks configuration: event -> list of matchers
HooksSettings = dict[str, list[HookMatcherSchema]]

# Convenience type aliases (mirror TS inferred types)
BashCommandHook = BashCommandHookSchema
PromptHook = PromptHookSchema
AgentHook = AgentHookSchema
HttpHook = HttpHookSchema
HookMatcher = HookMatcherSchema

# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_hook_command(d: dict) -> Optional[HookCommand]:
    """Parse a raw dict into a HookCommand.  Returns None for unknown types."""
    hook_type = d.get("type")
    if hook_type == "command":
        return BashCommandHookSchema(
            type="command",
            command=d.get("command", ""),
            if_=d.get("if"),
            shell=d.get("shell"),
            timeout=d.get("timeout"),
            status_message=d.get("statusMessage"),
            once=bool(d.get("once", False)),
            async_=bool(d.get("async", False)),
            async_rewake=bool(d.get("asyncRewake", False)),
        )
    if hook_type == "prompt":
        return PromptHookSchema(
            type="prompt",
            prompt=d.get("prompt", ""),
            if_=d.get("if"),
            timeout=d.get("timeout"),
            model=d.get("model"),
            status_message=d.get("statusMessage"),
            once=bool(d.get("once", False)),
        )
    if hook_type == "http":
        return HttpHookSchema(
            type="http",
            url=d.get("url", ""),
            if_=d.get("if"),
            timeout=d.get("timeout"),
            headers=d.get("headers"),
            allowed_env_vars=d.get("allowedEnvVars"),
            status_message=d.get("statusMessage"),
            once=bool(d.get("once", False)),
        )
    if hook_type == "agent":
        return AgentHookSchema(
            type="agent",
            prompt=d.get("prompt", ""),
            if_=d.get("if"),
            timeout=d.get("timeout"),
            model=d.get("model"),
            status_message=d.get("statusMessage"),
            once=bool(d.get("once", False)),
        )
    return None


def parse_hook_matcher(d: dict) -> HookMatcherSchema:
    """Parse a raw dict into a HookMatcherSchema."""
    raw_hooks = d.get("hooks", [])
    hooks = [
        h for raw in raw_hooks if (h := parse_hook_command(raw)) is not None
    ]
    return HookMatcherSchema(matcher=d.get("matcher"), hooks=hooks)


def parse_hooks_settings(d: dict) -> HooksSettings:
    """Parse a raw dict into a HooksSettings mapping."""
    result: HooksSettings = {}
    for event in HOOK_EVENTS:
        raw_list = d.get(event, [])
        if raw_list:
            result[event] = [parse_hook_matcher(m) for m in raw_list]
    return result


def validate_hooks_settings(d: Any) -> Optional[HooksSettings]:
    """Validate and parse hooks settings; return None on failure."""
    if not isinstance(d, dict):
        return None
    try:
        return parse_hooks_settings(d)
    except Exception:
        return None

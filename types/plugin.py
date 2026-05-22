"""Plugin types — mirrors src/types/plugin.ts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Optional, TypeAlias


@dataclass
class PluginAuthor:
    name: str
    email: Optional[str] = None
    url: Optional[str] = None


@dataclass
class CommandMetadata:
    description: Optional[str] = None
    argumentHint: Optional[str] = None
    whenToUse: Optional[str] = None
    allowedTools: Optional[list[str]] = None

    @property
    def argument_hint(self) -> Optional[str]:
        return self.argumentHint

    @property
    def when_to_use(self) -> Optional[str]:
        return self.whenToUse

    @property
    def allowed_tools(self) -> Optional[list[str]]:
        return self.allowedTools


@dataclass
class PluginManifest:
    name: str
    version: str
    description: str
    author: Optional[PluginAuthor] = None
    commandsPath: Optional[str] = None
    agentsPath: Optional[str] = None
    skillsPath: Optional[str] = None
    outputStylesPath: Optional[str] = None
    mcpServers: Optional[dict[str, Any]] = None
    lspServers: Optional[dict[str, Any]] = None
    hooks: Optional[dict] = None
    settings: Optional[dict[str, Any]] = None


@dataclass
class BuiltinPluginDefinition:
    """Built-in plugin that ships with the CLI."""
    name: str
    description: str
    version: Optional[str] = None
    skills: Optional[list] = None
    hooks: Optional[dict] = None
    mcpServers: Optional[dict[str, Any]] = None
    is_available: Optional[Callable[[], bool]] = None
    default_enabled: bool = True

    @property
    def isAvailable(self) -> Optional[Callable[[], bool]]:
        return self.is_available

    @property
    def defaultEnabled(self) -> bool:
        return self.default_enabled


@dataclass
class PluginRepository:
    url: str
    branch: str
    lastUpdated: Optional[str] = None
    commitSha: Optional[str] = None


@dataclass
class PluginConfig:
    repositories: dict[str, PluginRepository] = field(default_factory=dict)


@dataclass
class LoadedPlugin:
    name: str
    manifest: PluginManifest
    path: str
    source: str
    repository: str
    enabled: Optional[bool] = None
    is_builtin: bool = False
    sha: Optional[str] = None
    commandsPath: Optional[str] = None
    commandsPaths: Optional[list[str]] = None
    commandsMetadata: Optional[dict[str, CommandMetadata]] = None
    agentsPath: Optional[str] = None
    agentsPaths: Optional[list[str]] = None
    skillsPath: Optional[str] = None
    skillsPaths: Optional[list[str]] = None
    outputStylesPath: Optional[str] = None
    outputStylesPaths: Optional[list[str]] = None
    hooksConfig: Optional[dict[str, Any]] = None
    mcpServers: Optional[dict[str, Any]] = None
    lspServers: Optional[dict[str, Any]] = None
    settings: Optional[dict[str, Any]] = None

    @property
    def isBuiltin(self) -> bool:
        return self.is_builtin


PluginComponent = Literal["commands", "agents", "skills", "hooks", "output-styles"]


@dataclass
class PluginError:
    type: str
    source: str
    plugin: Optional[str] = None
    error: Optional[str] = None
    path: Optional[str] = None
    component: Optional[PluginComponent] = None
    gitUrl: Optional[str] = None
    authType: Optional[Literal["ssh", "https"]] = None
    operation: Optional[Literal["clone", "pull"]] = None
    url: Optional[str] = None
    details: Optional[str] = None
    manifestPath: Optional[str] = None
    parseError: Optional[str] = None
    validationErrors: Optional[list[str]] = None
    pluginId: Optional[str] = None
    marketplace: Optional[str] = None
    availableMarketplaces: Optional[list[str]] = None
    reason: Optional[str] = None
    serverName: Optional[str] = None
    validationError: Optional[str] = None
    duplicateOf: Optional[str] = None
    hookPath: Optional[str] = None
    mcpbPath: Optional[str] = None
    method: Optional[str] = None
    timeoutMs: Optional[int] = None
    blockedByBlocklist: Optional[bool] = None
    allowedSources: Optional[list[str]] = None
    dependency: Optional[str] = None
    installPath: Optional[str] = None
    exitCode: Optional[int] = None
    signal: Optional[str] = None


@dataclass
class PluginLoadResult:
    enabled: list[LoadedPlugin] = field(default_factory=list)
    disabled: list[LoadedPlugin] = field(default_factory=list)
    errors: list[PluginError] = field(default_factory=list)


def getPluginErrorMessage(error: PluginError) -> str:
    match error.type:
        case "generic-error":
            return error.error or "Plugin error"
        case "path-not-found":
            return f"Path not found: {error.path} ({error.component})"
        case "git-auth-failed":
            return f"Git authentication failed ({error.authType}): {error.gitUrl}"
        case "git-timeout":
            return f"Git {error.operation} timeout: {error.gitUrl}"
        case "network-error":
            suffix = f" - {error.details}" if error.details else ""
            return f"Network error: {error.url}{suffix}"
        case "manifest-parse-error":
            return f"Manifest parse error: {error.parseError}"
        case "manifest-validation-error":
            return f"Manifest validation failed: {', '.join(error.validationErrors or [])}"
        case "plugin-not-found":
            return f"Plugin {error.pluginId} not found in marketplace {error.marketplace}"
        case "marketplace-not-found":
            return f"Marketplace {error.marketplace} not found"
        case "marketplace-load-failed":
            return f"Marketplace {error.marketplace} failed to load: {error.reason}"
        case "mcp-config-invalid":
            return f"MCP server {error.serverName} invalid: {error.validationError}"
        case "mcp-server-suppressed-duplicate":
            duplicate_of = error.duplicateOf or "unknown"
            if duplicate_of.startswith("plugin:"):
                plugin_name = duplicate_of.split(":", 1)[1] or "?"
                duplicate_target = f'server provided by plugin "{plugin_name}"'
            else:
                duplicate_target = f'already-configured "{duplicate_of}"'
            return f'MCP server "{error.serverName}" skipped — same command/URL as {duplicate_target}'
        case "hook-load-failed":
            return f"Hook load failed: {error.reason}"
        case "component-load-failed":
            return f"{error.component} load failed from {error.path}: {error.reason}"
        case "mcpb-download-failed":
            return f"Failed to download MCPB from {error.url}: {error.reason}"
        case "mcpb-extract-failed":
            return f"Failed to extract MCPB {error.mcpbPath}: {error.reason}"
        case "mcpb-invalid-manifest":
            return f"MCPB manifest invalid at {error.mcpbPath}: {error.validationError}"
        case "lsp-config-invalid":
            return f'Plugin "{error.plugin}" has invalid LSP server config for "{error.serverName}": {error.validationError}'
        case "lsp-server-start-failed":
            return f'Plugin "{error.plugin}" failed to start LSP server "{error.serverName}": {error.reason}'
        case "lsp-server-crashed":
            if error.signal:
                return f'Plugin "{error.plugin}" LSP server "{error.serverName}" crashed with signal {error.signal}'
            return f'Plugin "{error.plugin}" LSP server "{error.serverName}" crashed with exit code {error.exitCode if error.exitCode is not None else "unknown"}'
        case "lsp-request-timeout":
            return f'Plugin "{error.plugin}" LSP server "{error.serverName}" timed out on {error.method} request after {error.timeoutMs}ms'
        case "lsp-request-failed":
            return f'Plugin "{error.plugin}" LSP server "{error.serverName}" {error.method} request failed: {error.error}'
        case "marketplace-blocked-by-policy":
            if error.blockedByBlocklist:
                return f"Marketplace '{error.marketplace}' is blocked by enterprise policy"
            return f"Marketplace '{error.marketplace}' is not in the allowed marketplace list"
        case "dependency-unsatisfied":
            hint = "disabled — enable it or remove the dependency" if error.reason == "not-enabled" else "not found in any configured marketplace"
            return f'Dependency "{error.dependency}" is {hint}'
        case "plugin-cache-miss":
            return f'Plugin "{error.plugin}" not cached at {error.installPath} — run /plugins to refresh'
        case _:
            return error.error or error.reason or error.type

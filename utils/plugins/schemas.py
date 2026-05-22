"""
Port of src/utils/plugins/schemas.ts

Type definitions and constants for the plugin system.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, TypedDict

# ── Official marketplace constants ──────────────────────────────────────────

ALLOWED_OFFICIAL_MARKETPLACE_NAMES: Set[str] = {
    "vivian-code-marketplace", "vivian-code-plugins", "vivian-plugins-official",
    "anthropic-marketplace", "anthropic-plugins", "agent-skills",
    "life-sciences", "knowledge-work-plugins",
}

BLOCKED_OFFICIAL_NAME_PATTERN = (
    r"(?:official[^a-z0-9]*(anthropic|vivian)|"
    r"(?:anthropic|vivian)[^a-z0-9]*official|"
    r"^(?:anthropic|vivian)[^a-z0-9]*(marketplace|plugins|official))"
)

OFFICIAL_GITHUB_ORG = "anthropics"

# ── Type aliases ────────────────────────────────────────────────────────────

PluginId = str
PluginScope = str  # "user" | "project" | "local" | "managed" | "flag"


class PluginAuthor(TypedDict, total=False):
    name: str
    email: Optional[str]
    url: Optional[str]


class PluginManifest(TypedDict, total=False):
    name: str
    version: Optional[str]
    description: Optional[str]
    author: Optional[PluginAuthor]
    homepage: Optional[str]
    repository: Optional[str]
    license: Optional[str]
    keywords: Optional[List[str]]
    dependencies: Optional[List[str]]
    hooks: Optional[str]
    commands: Optional[List[str]]
    agents: Optional[List[str]]
    skills: Optional[List[str]]
    outputStyles: Optional[List[str]]
    mcpServers: Optional[Any]
    lspServers: Optional[Any]
    channels: Optional[List[Dict[str, Any]]]
    userConfig: Optional[Dict[str, Any]]
    settings: Optional[Dict[str, Any]]


class PluginMarketplaceEntry(TypedDict, total=False):
    name: str
    description: Optional[str]
    version: Optional[str]
    source: Any
    category: Optional[str]
    tags: Optional[List[str]]
    dependencies: Optional[List[str]]
    lspServers: Optional[Any]
    strict: Optional[bool]


class PluginMarketplace(TypedDict, total=False):
    name: str
    plugins: List[PluginMarketplaceEntry]
    owner: Optional[PluginAuthor]
    allowCrossMarketplaceDependenciesOn: Optional[List[str]]
    forceRemoveDeletedPlugins: Optional[bool]


class MarketplaceSource(TypedDict, total=False):
    source: str
    url: Optional[str]
    repo: Optional[str]
    ref: Optional[str]
    path: Optional[str]
    package: Optional[str]
    name: Optional[str]
    plugins: Optional[List[Any]]
    hostPattern: Optional[str]
    pathPattern: Optional[str]
    headers: Optional[Dict[str, str]]
    sparsePaths: Optional[List[str]]


class KnownMarketplace(TypedDict, total=False):
    source: MarketplaceSource
    installLocation: Optional[str]
    lastUpdated: Optional[str]
    autoUpdate: Optional[bool]


KnownMarketplacesFile = Dict[str, KnownMarketplace]


class PluginInstallationEntry(TypedDict, total=False):
    version: str
    installedAt: str
    lastUpdated: str
    installPath: str
    gitCommitSha: Optional[str]
    scope: PluginScope
    projectPath: Optional[str]


InstalledPluginsFileV1 = Dict[str, Any]
InstalledPluginsFileV2 = Dict[str, Any]


class InstalledPlugin(TypedDict, total=False):
    version: str
    installedAt: str
    lastUpdated: str
    installPath: str
    gitCommitSha: Optional[str]


# ── Helper functions ────────────────────────────────────────────────────────

def isMarketplaceAutoUpdate(marketplace_name: str, entry: Dict[str, Any]) -> bool:
    """Check if a marketplace has autoUpdate enabled."""
    if entry.get("autoUpdate") is not None:
        return bool(entry["autoUpdate"])
    return marketplace_name.lower() in ALLOWED_OFFICIAL_MARKETPLACE_NAMES


def isBlockedOfficialName(name: str) -> bool:
    """Check if a name impersonates an official marketplace."""
    import re
    return bool(re.search(BLOCKED_OFFICIAL_NAME_PATTERN, name, re.IGNORECASE))


def validateOfficialNameSource(name: str, source: Dict[str, Any]) -> Optional[str]:
    """Validate that an official-looking name uses an approved source."""
    if not isBlockedOfficialName(name):
        return None
    source_type = source.get("source", "")
    if source_type not in ("github", "git"):
        return f'Name "{name}" looks official but source type is "{source_type}" (must be github or git)'
    if source_type == "github":
        repo = source.get("repo", "")
        if not repo.startswith(f"{OFFICIAL_GITHUB_ORG}/"):
            return f'Name "{name}" looks official but repo "{repo}" is not under {OFFICIAL_GITHUB_ORG}/'
    return None


def isLocalPluginSource(source: Any) -> bool:
    """Check if a plugin source is a local path."""
    return isinstance(source, str)


def isLocalMarketplaceSource(source: Dict[str, Any]) -> bool:
    """Check if a marketplace source is local (file or directory)."""
    return source.get("source") in ("file", "directory")


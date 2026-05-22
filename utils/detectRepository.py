"""Port of src/utils/detectRepository.ts."""
from __future__ import annotations

from typing import Any, Dict, Optional
import re


ParsedRepository = Dict[str, Any]
repositoryWithHostCache: dict[str, Optional[ParsedRepository]] = {}


def clearRepositoryCaches():
    repositoryWithHostCache.clear()


async def detectCurrentRepository():
    result = await detectCurrentRepositoryWithHost()
    if not result or result.get("host") != "github.com":
        return None
    return f"{result['owner']}/{result['name']}"


async def detectCurrentRepositoryWithHost():
    """Like detectCurrentRepository, but also returns the host (e.g. "github.com"
or a GHE hostname). Callers that need to construct URLs against a specific
GitHub host should use this variant."""
    from .cwd import get_cwd
    from .debug import log_for_debugging
    from .git import get_remote_url

    cwd = get_cwd()
    if cwd in repositoryWithHostCache:
        return repositoryWithHostCache.get(cwd)

    try:
        remote_url = await get_remote_url(cwd=cwd)
        log_for_debugging(f"Git remote URL: {remote_url}")
        if not remote_url:
            log_for_debugging("No git remote URL found")
            repositoryWithHostCache[cwd] = None
            return None

        parsed = parseGitRemote(remote_url)
        if parsed:
            log_for_debugging(
                f"Parsed repository: {parsed['host']}/{parsed['owner']}/{parsed['name']} from URL: {remote_url}"
            )
        else:
            log_for_debugging(f"Parsed repository: None from URL: {remote_url}")
        repositoryWithHostCache[cwd] = parsed
        return parsed
    except Exception as error:
        log_for_debugging(f"Error detecting repository: {error}")
        repositoryWithHostCache[cwd] = None
        return None


def getCachedRepository():
    """Synchronously returns the cached github.com repository for the current cwd
as "owner/name", or null if it hasn't been resolved yet or the host is not
github.com. Call detectCurrentRepository() first to populate the cache.

Callers construct github.com URLs, so GHE hosts are filtered out here."""
    from .cwd import get_cwd

    parsed = repositoryWithHostCache.get(get_cwd())
    if not parsed or parsed.get("host") != "github.com":
        return None
    return f"{parsed['owner']}/{parsed['name']}"


def parseGitRemote(input):
    """Parses a git remote URL into host, owner, and name components.
Accepts any host (github.com, GHE instances, etc.).

Supports:
https://host/owner/repo.git
git@host:owner/repo.git
ssh://git@host/owner/repo.git
git://host/owner/repo.git
https://host/owner/repo (no .git)

Note: repo names can contain dots (e.g., cc.kurs.web)"""
    trimmed = input.strip()

    ssh_match = re.match(r"^git@([^:]+):([^/]+)/([^/]+?)(?:\.git)?$", trimmed)
    if ssh_match:
        host = ssh_match.group(1)
        if not looksLikeRealHostname(host):
            return None
        return {
            "host": host,
            "owner": ssh_match.group(2),
            "name": ssh_match.group(3),
        }

    url_match = re.match(
        r"^(https?|ssh|git)://(?:[^@]+@)?([^/:]+(?::\d+)?)/([^/]+)/([^/]+?)(?:\.git)?$",
        trimmed,
    )
    if url_match:
        protocol = url_match.group(1)
        host_with_port = url_match.group(2)
        host_without_port = host_with_port.split(":", 1)[0]
        if not looksLikeRealHostname(host_without_port):
            return None
        host = host_with_port if protocol in ("https", "http") else host_without_port
        return {
            "host": host,
            "owner": url_match.group(3),
            "name": url_match.group(4),
        }

    return None


def parseGitHubRepository(input):
    """Parses a git remote URL or "owner/repo" string and returns "owner/repo".
Only returns results for github.com hosts — GHE URLs return null.
Use parseGitRemote() for GHE support.
Also accepts plain "owner/repo" strings for backward compatibility."""
    trimmed = input.strip()
    parsed = parseGitRemote(trimmed)
    if parsed:
        if parsed.get("host") != "github.com":
            return None
        return f"{parsed['owner']}/{parsed['name']}"

    if "://" not in trimmed and "@" not in trimmed and "/" in trimmed:
        parts = trimmed.split("/")
        if len(parts) == 2 and parts[0] and parts[1]:
            return f"{parts[0]}/{parts[1].removesuffix('.git')}"

    try:
        from .debug import log_for_debugging

        log_for_debugging(f"Could not parse repository from: {trimmed}")
    except Exception:
        pass
    return None


def looksLikeRealHostname(host):
    """Checks whether a hostname looks like a real domain name rather than an
SSH config alias. A simple dot-check is not enough because aliases like
"github.com-work" still contain a dot. We additionally require that the
last segment (the TLD) is purely alphabetic — real TLDs (com, org, io, net)
never contain hyphens or digits."""
    if "." not in host:
        return False
    last_segment = host.split(".")[-1]
    if not last_segment:
        return False
    return bool(re.match(r"^[a-zA-Z]+$", last_segment))


clear_repository_caches = clearRepositoryCaches
detect_current_repository = detectCurrentRepository
detect_current_repository_with_host = detectCurrentRepositoryWithHost
get_cached_repository = getCachedRepository
parse_git_remote = parseGitRemote
parse_github_repository = parseGitHubRepository
looks_like_real_hostname = looksLikeRealHostname


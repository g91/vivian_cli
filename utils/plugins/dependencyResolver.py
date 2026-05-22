"""
Port of src/utils/plugins/dependencyResolver.ts

Plugin dependency resolution — pure functions, no I/O.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from .pluginIdentifier import parsePluginIdentifier


INLINE_MARKETPLACE = "inline"

DependencyLookupResult = Dict[str, Any]
PluginId = str


class ResolutionResult:
    pass


def qualifyDependency(dep: str, declaring_plugin_id: str) -> str:
    """Normalize a dependency reference to fully-qualified 'name@marketplace' form."""
    parsed = parsePluginIdentifier(dep)
    if parsed.get("marketplace"):
        return dep
    mkt = parsePluginIdentifier(declaring_plugin_id).get("marketplace")
    if not mkt or mkt == INLINE_MARKETPLACE:
        return dep
    return f"{dep}@{mkt}"


async def resolveDependencyClosure(
    root_id: PluginId,
    lookup: Callable[[PluginId], Awaitable[Optional[DependencyLookupResult]]],
    already_enabled: Set[PluginId],
    allowed_cross_marketplaces: Set[str] = None,
) -> Dict[str, Any]:
    """Walk the transitive dependency closure of root_id via DFS."""
    if allowed_cross_marketplaces is None:
        allowed_cross_marketplaces = set()

    root_marketplace = parsePluginIdentifier(root_id).get("marketplace", "")
    closure: List[PluginId] = []
    visited: Set[PluginId] = set()
    stack: List[PluginId] = []

    async def _walk(id_: PluginId, required_by: PluginId) -> Optional[Dict[str, Any]]:
        if id_ != root_id and id_ in already_enabled:
            return None

        id_marketplace = parsePluginIdentifier(id_).get("marketplace", "")
        if id_marketplace and id_marketplace != root_marketplace and id_marketplace not in allowed_cross_marketplaces:
            return {"ok": False, "reason": "cross-marketplace", "dependency": id_, "requiredBy": required_by}

        if id_ in stack:
            return {"ok": False, "reason": "cycle", "chain": [*stack, id_]}

        if id_ in visited:
            return None
        visited.add(id_)

        entry = await lookup(id_)
        if not entry:
            return {"ok": False, "reason": "not-found", "missing": id_, "requiredBy": required_by}

        stack.append(id_)
        for raw_dep in entry.get("dependencies") or []:
            dep = qualifyDependency(raw_dep, id_)
            err = await _walk(dep, id_)
            if err:
                return err
        stack.pop()

        closure.append(id_)
        return None

    err = await _walk(root_id, root_id)
    if err:
        return err
    return {"ok": True, "closure": closure}


def verifyAndDemote(plugins: List[Any]) -> Dict[str, Any]:
    """Load-time safety net: verify all manifest dependencies are in the enabled set."""
    known = {p.source for p in plugins}
    enabled = {p.source for p in plugins if p.enabled}

    known_by_name: Set[str] = set()
    enabled_by_name: Dict[str, int] = {}
    for p in plugins:
        known_by_name.add(parsePluginIdentifier(p.source)["name"])
    for id_ in enabled:
        n = parsePluginIdentifier(id_)["name"]
        enabled_by_name[n] = enabled_by_name.get(n, 0) + 1

    errors: List[Dict[str, Any]] = []

    changed = True
    while changed:
        changed = False
        for p in plugins:
            if p.source not in enabled:
                continue
            for raw_dep in p.manifest.get("dependencies") or []:
                dep = qualifyDependency(raw_dep, p.source)
                is_bare = not parsePluginIdentifier(dep).get("marketplace")
                satisfied = (enabled_by_name.get(dep, 0) > 0) if is_bare else (dep in enabled)
                if not satisfied:
                    enabled.discard(p.source)
                    count = enabled_by_name.get(p.name, 0)
                    if count <= 1:
                        enabled_by_name.pop(p.name, None)
                    else:
                        enabled_by_name[p.name] = count - 1
                    errors.append({
                        "type": "dependency-unsatisfied",
                        "source": p.source,
                        "plugin": p.name,
                        "dependency": dep,
                        "reason": "not-enabled" if (is_bare and dep in known_by_name) or (not is_bare and dep in known) else "not-found",
                    })
                    changed = True
                    break

    demoted = {p.source for p in plugins if p.enabled and p.source not in enabled}
    return {"demoted": demoted, "errors": errors}


def findReverseDependents(plugin_id: PluginId, plugins: List[Any]) -> List[str]:
    """Find all enabled plugins that declare plugin_id as a dependency."""
    target_name = parsePluginIdentifier(plugin_id)["name"]
    result: List[str] = []
    for p in plugins:
        if not p.enabled or p.source == plugin_id:
            continue
        for d in p.manifest.get("dependencies") or []:
            qualified = qualifyDependency(d, p.source)
            if parsePluginIdentifier(qualified).get("marketplace"):
                if qualified == plugin_id:
                    result.append(p.name)
                    break
            elif qualified == target_name:
                result.append(p.name)
                break
    return result


def getEnabledPluginIdsForScope(setting_source: str) -> Set[PluginId]:
    """Build the set of plugin IDs currently enabled at a given settings scope."""
    try:
        from ..settings.settings import getSettingsForSource
        settings = getSettingsForSource(setting_source)
        if not settings or "enabledPlugins" not in settings:
            return set()
        return {
            k for k, v in settings["enabledPlugins"].items()
            if v is True or isinstance(v, list)
        }
    except Exception:
        return set()


def formatDependencyCountSuffix(installed_deps: List[str]) -> str:
    """Format the '(+ N dependencies)' suffix for install success messages."""
    if not installed_deps:
        return ""
    n = len(installed_deps)
    return f" (+ {n} {'dependency' if n == 1 else 'dependencies'})"


def formatReverseDependentsSuffix(rdeps: Optional[List[str]]) -> str:
    """Format the 'warning: required by X, Y' suffix for uninstall/disable results."""
    if not rdeps:
        return ""
    return f" — warning: required by {', '.join(rdeps)}"


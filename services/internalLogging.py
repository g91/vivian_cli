"""Internal logging utilities — mirrors src/services/internalLogging.ts."""
from __future__ import annotations

import asyncio
import functools
import os
import re
from typing import Optional


@functools.lru_cache(maxsize=1)
def _get_kubernetes_namespace_sync() -> Optional[str]:
    if os.environ.get("USER_TYPE") != "ant":
        return None
    namespace_path = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
    try:
        with open(namespace_path, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "namespace not found"


async def getKubernetesNamespace() -> Optional[str]:
    """Get the current Kubernetes namespace.

    Returns None on laptops/local development.
    Mirrors getKubernetesNamespace() from internalLogging.ts.
    """
    return await asyncio.to_thread(_get_kubernetes_namespace_sync)


@functools.lru_cache(maxsize=1)
def _get_container_id_sync() -> Optional[str]:
    if os.environ.get("USER_TYPE") != "ant":
        return None
    container_id_path = "/proc/self/mountinfo"
    pattern = re.compile(r"(?:/docker/containers/|/sandboxes/)([0-9a-f]{64})")
    try:
        with open(container_id_path, encoding="utf-8") as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    return match.group(1)
        return "container ID not found in mountinfo"
    except Exception:
        return "container ID not found"


async def getContainerId() -> Optional[str]:
    """Get the OCI container ID from within a running container.

    Mirrors getContainerId() from internalLogging.ts.
    """
    return await asyncio.to_thread(_get_container_id_sync)


async def logPermissionContextForAnts(
    tool_permission_context: Optional[dict],
    moment: str,  # 'summary' | 'initialization'
) -> None:
    """Log an event with the current namespace and tool permission context.

    Only runs for Ant employees (USER_TYPE=ant).
    Mirrors logPermissionContextForAnts() from internalLogging.ts.
    """
    if os.environ.get("USER_TYPE") != "ant":
        return

    from .analytics.index import logEvent
    from ..utils.slowOperations import jsonStringify

    logEvent("tengu_internal_record_permission_context", {
        "moment": moment,
        "namespace": await getKubernetesNamespace(),
        "toolPermissionContext": jsonStringify(tool_permission_context),
        "containerId": await getContainerId(),
    })


get_kubernetes_namespace = getKubernetesNamespace
get_container_id = getContainerId
log_permission_context_for_ants = logPermissionContextForAnts

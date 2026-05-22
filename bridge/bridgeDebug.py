"""Port of src/bridge/bridgeDebug.ts

Ant-only fault injection for manually testing bridge recovery paths.
"""
from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Literal, Optional


BridgeFaultMethod = Literal[
    "pollForWork",
    "registerBridgeEnvironment",
    "reconnectSession",
    "heartbeatWork",
]
BridgeFaultKind = Literal["fatal", "transient"]


class BridgeFault:
    def __init__(
        self,
        method: BridgeFaultMethod,
        kind: BridgeFaultKind,
        status: int,
        error_type: Optional[str] = None,
        count: int = 1,
    ) -> None:
        self.method = method
        self.kind = kind
        self.status = status
        self.error_type = error_type
        self.count = count


class BridgeDebugHandle:
    def __init__(
        self,
        fire_close: Callable[[int], None],
        force_reconnect: Callable[[], None],
        inject_fault: Callable[[BridgeFault], None],
        wake_poll_loop: Callable[[], None],
        describe: Callable[[], str],
    ) -> None:
        self.fireClose = fire_close
        self.forceReconnect = force_reconnect
        self.injectFault = inject_fault
        self.wakePollLoop = wake_poll_loop
        self.describe = describe


_debug_handle: Optional[BridgeDebugHandle] = None
_fault_queue: List[BridgeFault] = []


def registerBridgeDebugHandle(h: BridgeDebugHandle) -> None:
    global _debug_handle
    _debug_handle = h


def clearBridgeDebugHandle() -> None:
    global _debug_handle
    _debug_handle = None
    _fault_queue.clear()


def getBridgeDebugHandle() -> Optional[BridgeDebugHandle]:
    return _debug_handle


def injectBridgeFault(fault: BridgeFault) -> None:
    _fault_queue.append(fault)
    try:
        from ..utils.debug import log_for_debugging
        extra = f"/{fault.error_type}" if fault.error_type else ""
        log_for_debugging(
            f"[bridge:debug] Queued fault: {fault.method} {fault.kind}/{fault.status}{extra} ×{fault.count}"
        )
    except Exception:
        pass


def wrapApiForFaultInjection(api: Any) -> Any:
    """
    Wrap a BridgeApiClient so each call first checks the fault queue.
    Only called when USER_TYPE == 'ant'.
    """
    if os.environ.get("USER_TYPE") != "ant":
        return api

    def _consume(method: str) -> Optional[BridgeFault]:
        for i, f in enumerate(_fault_queue):
            if f.method == method:
                f.count -= 1
                if f.count <= 0:
                    _fault_queue.pop(i)
                return f
        return None

    def _throw_fault(fault: BridgeFault, context: str) -> None:
        try:
            from ..utils.debug import log_for_debugging
            log_for_debugging(
                f"[bridge:debug] Injecting {fault.kind} fault into {context}: "
                f"status={fault.status} errorType={fault.error_type or 'none'}"
            )
        except Exception:
            pass
        if fault.kind == "fatal":
            try:
                from .bridgeApi import BridgeFatalError
                raise BridgeFatalError(
                    f"[injected] {context} {fault.status}",
                    fault.status,
                    fault.error_type,
                )
            except ImportError:
                raise RuntimeError(f"[injected fatal] {context} {fault.status}")
        raise RuntimeError(f"[injected transient] {context} {fault.status}")

    class WrappedApi:
        async def pollForWork(self, env_id, secret, signal, reclaim_ms):
            f = _consume("pollForWork")
            if f:
                _throw_fault(f, "Poll")
            return await api.pollForWork(env_id, secret, signal, reclaim_ms)

        async def registerBridgeEnvironment(self, config):
            f = _consume("registerBridgeEnvironment")
            if f:
                _throw_fault(f, "Registration")
            return await api.registerBridgeEnvironment(config)

        async def reconnectSession(self, env_id, session_id):
            f = _consume("reconnectSession")
            if f:
                _throw_fault(f, "ReconnectSession")
            return await api.reconnectSession(env_id, session_id)

        async def heartbeatWork(self, env_id, work_id, token):
            f = _consume("heartbeatWork")
            if f:
                _throw_fault(f, "Heartbeat")
            return await api.heartbeatWork(env_id, work_id, token)

        def __getattr__(self, name):
            return getattr(api, name)

    return WrappedApi()

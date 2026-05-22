"""Permission context — mirrors src/hooks/toolPermission/PermissionContext.ts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, Optional, Protocol, TypeVar

from ...types.permissions import PermissionAllowDecision, PermissionDenyDecision, PermissionDecision
from ...utils.permissions.PermissionUpdate import applyPermissionUpdates, persistPermissionUpdates
from .permissionLogging import logPermissionDecision


T = TypeVar("T")
PermissionApprovalSource = dict[str, Any]
PermissionRejectionSource = dict[str, Any]

REJECT_MESSAGE = "Permission denied."
REJECT_MESSAGE_WITH_REASON_PREFIX = "Permission denied: "
SUBAGENT_REJECT_MESSAGE = "Subagent permission denied."
SUBAGENT_REJECT_MESSAGE_WITH_REASON_PREFIX = "Subagent permission denied: "


class PermissionQueueOps(Protocol):
    def push(self, item: dict[str, Any]) -> None: ...
    def remove(self, toolUseID: str) -> None: ...
    def update(self, toolUseID: str, patch: dict[str, Any]) -> None: ...


class ResolveOnce(Generic[T]):
    def __init__(self, resolve: Callable[[T], None]):
        self._resolve = resolve
        self._claimed = False
        self._delivered = False

    def resolve(self, value: T) -> None:
        if self._delivered:
            return
        self._delivered = True
        self._claimed = True
        self._resolve(value)

    def isResolved(self) -> bool:
        return self._claimed

    def claim(self) -> bool:
        if self._claimed:
            return False
        self._claimed = True
        return True


def createResolveOnce(resolve: Callable[[T], None]) -> ResolveOnce[T]:
    return ResolveOnce(resolve)


@dataclass(slots=True)
class PermissionContext:
    tool: Any
    input: dict[str, Any]
    toolUseContext: Any
    assistantMessage: Any
    messageId: str
    toolUseID: str
    setToolPermissionContext: Callable[[dict[str, Any]], None]
    queueOps: PermissionQueueOps | None = None

    def logDecision(
        self,
        args: dict[str, Any],
        opts: dict[str, Any] | None = None,
    ) -> None:
        opts = opts or {}
        logPermissionDecision(
            {
                "tool": self.tool,
                "input": opts.get("input", self.input),
                "toolUseContext": self.toolUseContext,
                "messageId": self.messageId,
                "toolUseID": self.toolUseID,
            },
            args,
            opts.get("permissionPromptStartTimeMs"),
        )

    def logCancelled(self) -> None:
        self.logDecision({"decision": "reject", "source": {"type": "user_abort"}})

    async def persistPermissions(self, updates: list[dict[str, Any]]) -> bool:
        if not updates:
            return False

        get_settings_for_source = _lookup(self.toolUseContext, "getSettingsForSource")
        update_settings_for_source = _lookup(self.toolUseContext, "updateSettingsForSource")
        if callable(get_settings_for_source) and callable(update_settings_for_source):
            persistPermissionUpdates(updates, get_settings_for_source, update_settings_for_source)

        app_state = _call_or_none(_lookup(self.toolUseContext, "getAppState")) or {}
        current_context = _app_state_get(app_state, "toolPermissionContext") or {}
        next_context = applyPermissionUpdates(dict(current_context), updates)
        self.setToolPermissionContext(next_context)
        return any(_supports_persistence(update.get("destination")) for update in updates)

    def resolveIfAborted(self, resolve: Callable[[PermissionDecision], None]) -> bool:
        signal = _abort_signal(self.toolUseContext)
        if signal is None or not getattr(signal, "aborted", False):
            return False
        self.logCancelled()
        resolve(self.cancelAndAbort(None, True))
        return True

    def cancelAndAbort(
        self,
        feedback: str | None = None,
        isAbort: bool | None = None,
        contentBlocks: list[Any] | None = None,
    ) -> dict[str, Any]:
        is_subagent = bool(_lookup(self.toolUseContext, "agentId"))
        if feedback:
            base_message = (
                SUBAGENT_REJECT_MESSAGE_WITH_REASON_PREFIX if is_subagent else REJECT_MESSAGE_WITH_REASON_PREFIX
            ) + feedback
        else:
            base_message = SUBAGENT_REJECT_MESSAGE if is_subagent else REJECT_MESSAGE

        if isAbort or (not feedback and not contentBlocks and not is_subagent):
            abort_controller = _lookup(self.toolUseContext, "abortController")
            if abort_controller is not None and hasattr(abort_controller, "abort"):
                abort_controller.abort()

        return {
            "behavior": "ask",
            "message": base_message,
            "contentBlocks": contentBlocks,
        }

    async def tryClassifier(
        self,
        pendingClassifierCheck: Any | None,
        updatedInput: dict[str, Any] | None,
    ) -> PermissionDecision | None:
        classifier = _lookup(self.toolUseContext, "tryClassifier")
        if callable(classifier):
            return await classifier(pendingClassifierCheck, updatedInput)
        return None

    async def runHooks(
        self,
        permissionMode: str | None,
        suggestions: list[dict[str, Any]] | None,
        updatedInput: dict[str, Any] | None = None,
        permissionPromptStartTimeMs: int | None = None,
    ) -> PermissionDecision | None:
        hook_runner = _lookup(self.toolUseContext, "executePermissionRequestHooks")
        if not callable(hook_runner):
            return None

        result = await hook_runner(
            _tool_name(self.tool),
            self.toolUseID,
            self.input,
            self.toolUseContext,
            permissionMode,
            suggestions,
            _abort_signal(self.toolUseContext),
        )
        if not isinstance(result, dict):
            return None

        decision = result.get("permissionRequestResult")
        if not isinstance(decision, dict):
            return None
        if decision.get("behavior") == "allow":
            final_input = decision.get("updatedInput") or updatedInput or self.input
            return await self.handleHookAllow(
                final_input,
                decision.get("updatedPermissions") or [],
                permissionPromptStartTimeMs,
            )
        if decision.get("behavior") == "deny":
            self.logDecision(
                {"decision": "reject", "source": {"type": "hook"}},
                {"permissionPromptStartTimeMs": permissionPromptStartTimeMs},
            )
            return self.buildDeny(
                decision.get("message") or "Permission denied by hook",
                {"type": "hook", "hookName": "PermissionRequest", "reason": decision.get("message")},
            )
        return None

    def buildAllow(
        self,
        updatedInput: dict[str, Any],
        opts: dict[str, Any] | None = None,
    ) -> PermissionAllowDecision:
        opts = opts or {}
        return PermissionAllowDecision(
            updatedInput=updatedInput,
            userModified=opts.get("userModified", False),
            decisionReason=opts.get("decisionReason"),
            acceptFeedback=opts.get("acceptFeedback"),
            contentBlocks=opts.get("contentBlocks"),
        )

    def buildDeny(
        self,
        message: str,
        decisionReason: dict[str, Any],
    ) -> PermissionDenyDecision:
        return PermissionDenyDecision(message=message, decisionReason=decisionReason)

    async def handleUserAllow(
        self,
        updatedInput: dict[str, Any],
        permissionUpdates: list[dict[str, Any]],
        feedback: str | None = None,
        permissionPromptStartTimeMs: int | None = None,
        contentBlocks: list[Any] | None = None,
        decisionReason: Any | None = None,
    ) -> PermissionAllowDecision:
        accepted_permanent_updates = await self.persistPermissions(permissionUpdates)
        self.logDecision(
            {
                "decision": "accept",
                "source": {"type": "user", "permanent": accepted_permanent_updates},
            },
            {"input": updatedInput, "permissionPromptStartTimeMs": permissionPromptStartTimeMs},
        )
        user_modified = updatedInput != self.input
        trimmed_feedback = feedback.strip() if isinstance(feedback, str) else None
        return self.buildAllow(
            updatedInput,
            {
                "userModified": user_modified,
                "decisionReason": decisionReason,
                "acceptFeedback": trimmed_feedback or None,
                "contentBlocks": contentBlocks,
            },
        )

    async def handleHookAllow(
        self,
        finalInput: dict[str, Any],
        permissionUpdates: list[dict[str, Any]],
        permissionPromptStartTimeMs: int | None = None,
    ) -> PermissionAllowDecision:
        accepted_permanent_updates = await self.persistPermissions(permissionUpdates)
        self.logDecision(
            {
                "decision": "accept",
                "source": {"type": "hook", "permanent": accepted_permanent_updates},
            },
            {"input": finalInput, "permissionPromptStartTimeMs": permissionPromptStartTimeMs},
        )
        return self.buildAllow(
            finalInput,
            {"decisionReason": {"type": "hook", "hookName": "PermissionRequest"}},
        )

    def pushToQueue(self, item: dict[str, Any]) -> None:
        if self.queueOps is not None:
            self.queueOps.push(item)

    def removeFromQueue(self) -> None:
        if self.queueOps is not None:
            self.queueOps.remove(self.toolUseID)

    def updateQueueItem(self, patch: dict[str, Any]) -> None:
        if self.queueOps is not None:
            self.queueOps.update(self.toolUseID, patch)

    def canUseTool(self, toolName: str) -> bool:
        app_state = _call_or_none(_lookup(self.toolUseContext, "getAppState")) or {}
        permission_context = _app_state_get(app_state, "toolPermissionContext") or {}
        deny_rules = permission_context.get("alwaysDenyRules", {}) or {}
        for rules in deny_rules.values():
            if any(str(rule).split(":", 1)[0] == toolName for rule in (rules or [])):
                return False
        return True


def createPermissionContext(
    tool: Any,
    input: dict[str, Any],
    toolUseContext: Any,
    assistantMessage: Any,
    toolUseID: str,
    setToolPermissionContext: Callable[[dict[str, Any]], None],
    queueOps: PermissionQueueOps | None = None,
) -> PermissionContext:
    message_id = _message_id(assistantMessage)
    return PermissionContext(
        tool=tool,
        input=input,
        toolUseContext=toolUseContext,
        assistantMessage=assistantMessage,
        messageId=message_id,
        toolUseID=toolUseID,
        setToolPermissionContext=setToolPermissionContext,
        queueOps=queueOps,
    )


class _QueueOpsImpl:
    def __init__(self, setToolUseConfirmQueue: Callable[[Callable[[list[dict[str, Any]]], list[dict[str, Any]]]], None]):
        self._setter = setToolUseConfirmQueue

    def push(self, item: dict[str, Any]) -> None:
        self._setter(lambda queue: [*queue, item])

    def remove(self, toolUseID: str) -> None:
        self._setter(lambda queue: [item for item in queue if item.get("toolUseID") != toolUseID])

    def update(self, toolUseID: str, patch: dict[str, Any]) -> None:
        self._setter(
            lambda queue: [
                {**item, **patch} if item.get("toolUseID") == toolUseID else item for item in queue
            ]
        )


def createPermissionQueueOps(
    setToolUseConfirmQueue: Callable[[Callable[[list[dict[str, Any]]], list[dict[str, Any]]]], None],
) -> PermissionQueueOps:
    return _QueueOpsImpl(setToolUseConfirmQueue)


def _lookup(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _call_or_none(candidate: Any) -> Any:
    return candidate() if callable(candidate) else None


def _message_id(message: Any) -> str:
    if isinstance(message, dict):
        inner = message.get("message") or {}
        return str(inner.get("id") or message.get("id") or "")
    inner = getattr(message, "message", None)
    return str(getattr(inner, "id", None) or getattr(message, "id", ""))


def _abort_signal(tool_use_context: Any) -> Any:
    abort_controller = _lookup(tool_use_context, "abortController")
    return getattr(abort_controller, "signal", None) if abort_controller is not None else None


def _app_state_get(app_state: Any, key: str) -> Any:
    if isinstance(app_state, dict):
        return app_state.get(key)
    return getattr(app_state, key, None)


def _supports_persistence(destination: Any) -> bool:
    return destination in {"localSettings", "projectSettings", "userSettings", "cliArg"}


def _tool_name(tool: Any) -> str:
    if isinstance(tool, dict):
        return str(tool.get("name", "unknown"))
    return str(getattr(tool, "name", "unknown"))


permission_context = PermissionContext
create_resolve_once = createResolveOnce
create_permission_context = createPermissionContext
create_permission_queue_ops = createPermissionQueueOps

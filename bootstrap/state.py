"""Port of src/bootstrap/state.ts

Global session state. Single module-level STATE dict mirrors the TS State type.
All getters/setters are module-level functions wrapping STATE for parity.

DO NOT ADD MORE STATE HERE — BE JUDICIOUS WITH GLOBAL STATE.
"""
from __future__ import annotations

import os
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Set

# ---------------------------------------------------------------------------
# Signal primitive (replaces src/utils/signal.ts createSignal)
# ---------------------------------------------------------------------------

class _Signal:
    """Simple publish/subscribe with .emit(), .subscribe(), .clear()."""

    def __init__(self):
        self._listeners: List[Callable] = []

    def subscribe(self, cb: Callable) -> Callable:
        self._listeners.append(cb)
        def unsubscribe():
            try:
                self._listeners.remove(cb)
            except ValueError:
                pass
        return unsubscribe

    def emit(self, *args) -> None:
        for cb in list(self._listeners):
            try:
                cb(*args)
            except Exception:
                pass

    def clear(self) -> None:
        self._listeners.clear()


# ---------------------------------------------------------------------------
# Type stubs (TS types become plain dicts / Any in Python)
# ---------------------------------------------------------------------------

SessionId = str
ModelSetting = Any
ModelUsage = Dict[str, Any]
ModelStrings = Any
SettingSource = str
HookEvent = str
AgentColorName = str
SessionCronTask = Dict[str, Any]
InvokedSkillInfo = Dict[str, Any]
ChannelEntry = Dict[str, Any]

ALLOWED_SETTING_SOURCES: List[SettingSource] = [
    "userSettings",
    "projectSettings",
    "localSettings",
    "flagSettings",
    "policySettings",
]

# ---------------------------------------------------------------------------
# Initial state factory
# ---------------------------------------------------------------------------

def _get_resolved_cwd() -> str:
    try:
        raw = os.getcwd()
        return os.path.realpath(raw)
    except Exception:
        return os.getcwd()


def _get_initial_state() -> Dict[str, Any]:
    resolved_cwd = _get_resolved_cwd()
    now = int(time.time() * 1000)
    return {
        "originalCwd": resolved_cwd,
        "projectRoot": resolved_cwd,
        "totalCostUSD": 0.0,
        "totalAPIDuration": 0,
        "totalAPIDurationWithoutRetries": 0,
        "totalToolDuration": 0,
        "turnHookDurationMs": 0,
        "turnToolDurationMs": 0,
        "turnClassifierDurationMs": 0,
        "turnToolCount": 0,
        "turnHookCount": 0,
        "turnClassifierCount": 0,
        "startTime": now,
        "lastInteractionTime": now,
        "totalLinesAdded": 0,
        "totalLinesRemoved": 0,
        "hasUnknownModelCost": False,
        "cwd": resolved_cwd,
        "modelUsage": {},
        "mainLoopModelOverride": None,
        "initialMainLoopModel": None,
        "modelStrings": None,
        "isInteractive": False,
        "kairosActive": False,
        "strictToolResultPairing": False,
        "sdkAgentProgressSummariesEnabled": False,
        "userMsgOptIn": False,
        "clientType": "cli",
        "sessionSource": None,
        "questionPreviewFormat": None,
        "flagSettingsPath": None,
        "flagSettingsInline": None,
        "allowedSettingSources": list(ALLOWED_SETTING_SOURCES),
        "sessionIngressToken": None,
        "oauthTokenFromFd": None,
        "apiKeyFromFd": None,
        # Telemetry state
        "meter": None,
        "sessionCounter": None,
        "locCounter": None,
        "prCounter": None,
        "commitCounter": None,
        "costCounter": None,
        "tokenCounter": None,
        "codeEditToolDecisionCounter": None,
        "activeTimeCounter": None,
        "statsStore": None,
        "sessionId": str(uuid.uuid4()),
        "parentSessionId": None,
        # Logger state
        "loggerProvider": None,
        "eventLogger": None,
        # Meter/tracer provider state
        "meterProvider": None,
        "tracerProvider": None,
        # Agent color state
        "agentColorMap": {},
        "agentColorIndex": 0,
        # Last API request for bug reports
        "lastAPIRequest": None,
        "lastAPIRequestMessages": None,
        "lastClassifierRequests": None,
        "cachedvivianMdContent": None,
        # In-memory error log
        "inMemoryErrorLog": [],
        "inlinePlugins": [],
        "chromeFlagOverride": None,
        "useCoworkPlugins": False,
        "sessionBypassPermissionsMode": False,
        "scheduledTasksEnabled": False,
        "sessionCronTasks": [],
        "sessionCreatedTeams": set(),
        "sessionTrustAccepted": False,
        "sessionPersistenceDisabled": False,
        "hasExitedPlanMode": False,
        "needsPlanModeExitAttachment": False,
        "needsAutoModeExitAttachment": False,
        "lspRecommendationShownThisSession": False,
        "initJsonSchema": None,
        "registeredHooks": None,
        "planSlugCache": {},
        "teleportedSessionInfo": None,
        "invokedSkills": {},
        "slowOperations": [],
        "sdkBetas": None,
        "mainThreadAgentType": None,
        "isRemoteMode": False,
        "directConnectServerUrl": None,
        "systemPromptSectionCache": {},
        "lastEmittedDate": None,
        "additionalDirectoriesForvivianMd": [],
        "allowedChannels": [],
        "hasDevChannels": False,
        "sessionProjectDir": None,
        "promptCache1hAllowlist": None,
        "promptCache1hEligible": None,
        "afkModeHeaderLatched": None,
        "fastModeHeaderLatched": None,
        "cacheEditingHeaderLatched": None,
        "thinkingClearLatched": None,
        "promptId": None,
        "lastMainRequestId": None,
        "lastApiCompletionTimestamp": None,
        "pendingPostCompaction": False,
    }


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_STATE: Dict[str, Any] = _get_initial_state()

_session_switched = _Signal()
onSessionSwitch = _session_switched.subscribe

# Turn-token tracking (module-level, not in STATE — ephemeral)
_output_tokens_at_turn_start = 0
_current_turn_token_budget: Optional[int] = None
_budget_continuation_count = 0

# Scroll drain state
_scroll_draining = False
_scroll_drain_timer: Optional[Any] = None
_SCROLL_DRAIN_IDLE_MS = 150

# Interaction time dirty flag
_interaction_time_dirty = False


# ---------------------------------------------------------------------------
# Session ID
# ---------------------------------------------------------------------------

def getSessionId() -> SessionId:
    return _STATE["sessionId"]


def regenerateSessionId(options: Optional[Dict[str, Any]] = None) -> SessionId:
    if options and options.get("setCurrentAsParent"):
        _STATE["parentSessionId"] = _STATE["sessionId"]
    _STATE["planSlugCache"].pop(_STATE["sessionId"], None)
    _STATE["sessionId"] = str(uuid.uuid4())
    _STATE["sessionProjectDir"] = None
    return _STATE["sessionId"]


def getParentSessionId() -> Optional[SessionId]:
    return _STATE["parentSessionId"]


def switchSession(session_id: SessionId, project_dir: Optional[str] = None) -> None:
    _STATE["planSlugCache"].pop(_STATE["sessionId"], None)
    _STATE["sessionId"] = session_id
    _STATE["sessionProjectDir"] = project_dir
    _session_switched.emit(session_id)


def getSessionProjectDir() -> Optional[str]:
    return _STATE["sessionProjectDir"]


# ---------------------------------------------------------------------------
# Working directory / project root
# ---------------------------------------------------------------------------

def getOriginalCwd() -> str:
    return _STATE["originalCwd"]


def getProjectRoot() -> str:
    return _STATE["projectRoot"]


def setOriginalCwd(cwd: str) -> None:
    _STATE["originalCwd"] = cwd


def setProjectRoot(cwd: str) -> None:
    _STATE["projectRoot"] = cwd


def getCwdState() -> str:
    return _STATE["cwd"]


def setCwdState(cwd: str) -> None:
    _STATE["cwd"] = cwd


def getDirectConnectServerUrl() -> Optional[str]:
    return _STATE["directConnectServerUrl"]


def setDirectConnectServerUrl(url: str) -> None:
    _STATE["directConnectServerUrl"] = url


# ---------------------------------------------------------------------------
# Cost / duration tracking
# ---------------------------------------------------------------------------

def addToTotalDurationState(duration: int, duration_without_retries: int) -> None:
    _STATE["totalAPIDuration"] += duration
    _STATE["totalAPIDurationWithoutRetries"] += duration_without_retries


def resetTotalDurationStateAndCost_FOR_TESTS_ONLY() -> None:
    _STATE["totalAPIDuration"] = 0
    _STATE["totalAPIDurationWithoutRetries"] = 0
    _STATE["totalCostUSD"] = 0.0


def addToTotalCostState(cost: float, model_usage: ModelUsage, model: str) -> None:
    _STATE["modelUsage"][model] = model_usage
    _STATE["totalCostUSD"] += cost


def getTotalCostUSD() -> float:
    return _STATE["totalCostUSD"]


def getTotalAPIDuration() -> int:
    return _STATE["totalAPIDuration"]


def getTotalDuration() -> int:
    return int(time.time() * 1000) - _STATE["startTime"]


def getTotalAPIDurationWithoutRetries() -> int:
    return _STATE["totalAPIDurationWithoutRetries"]


def getTotalToolDuration() -> int:
    return _STATE["totalToolDuration"]


def addToToolDuration(duration: int) -> None:
    _STATE["totalToolDuration"] += duration
    _STATE["turnToolDurationMs"] += duration
    _STATE["turnToolCount"] += 1


def getTurnHookDurationMs() -> int:
    return _STATE["turnHookDurationMs"]


def addToTurnHookDuration(duration: int) -> None:
    _STATE["turnHookDurationMs"] += duration
    _STATE["turnHookCount"] += 1


def resetTurnHookDuration() -> None:
    _STATE["turnHookDurationMs"] = 0
    _STATE["turnHookCount"] = 0


def getTurnHookCount() -> int:
    return _STATE["turnHookCount"]


def getTurnToolDurationMs() -> int:
    return _STATE["turnToolDurationMs"]


def resetTurnToolDuration() -> None:
    _STATE["turnToolDurationMs"] = 0
    _STATE["turnToolCount"] = 0


def getTurnToolCount() -> int:
    return _STATE["turnToolCount"]


def getTurnClassifierDurationMs() -> int:
    return _STATE["turnClassifierDurationMs"]


def addToTurnClassifierDuration(duration: int) -> None:
    _STATE["turnClassifierDurationMs"] += duration
    _STATE["turnClassifierCount"] += 1


def resetTurnClassifierDuration() -> None:
    _STATE["turnClassifierDurationMs"] = 0
    _STATE["turnClassifierCount"] = 0


def getTurnClassifierCount() -> int:
    return _STATE["turnClassifierCount"]


def getStatsStore() -> Optional[Any]:
    return _STATE["statsStore"]


def setStatsStore(store: Optional[Any]) -> None:
    _STATE["statsStore"] = store


# ---------------------------------------------------------------------------
# Interaction time
# ---------------------------------------------------------------------------

def updateLastInteractionTime(immediate: bool = False) -> None:
    global _interaction_time_dirty
    if immediate:
        _flush_interaction_time_inner()
    else:
        _interaction_time_dirty = True


def flushInteractionTime() -> None:
    global _interaction_time_dirty
    if _interaction_time_dirty:
        _flush_interaction_time_inner()


def _flush_interaction_time_inner() -> None:
    global _interaction_time_dirty
    _STATE["lastInteractionTime"] = int(time.time() * 1000)
    _interaction_time_dirty = False


def getLastInteractionTime() -> int:
    return _STATE["lastInteractionTime"]


# ---------------------------------------------------------------------------
# Lines changed
# ---------------------------------------------------------------------------

def addToTotalLinesChanged(added: int, removed: int) -> None:
    _STATE["totalLinesAdded"] += added
    _STATE["totalLinesRemoved"] += removed


def getTotalLinesAdded() -> int:
    return _STATE["totalLinesAdded"]


def getTotalLinesRemoved() -> int:
    return _STATE["totalLinesRemoved"]


# ---------------------------------------------------------------------------
# Token counts (computed from modelUsage)
# ---------------------------------------------------------------------------

def _sum_usage(key: str) -> int:
    return sum(v.get(key, 0) for v in _STATE["modelUsage"].values() if isinstance(v, dict))


def getTotalInputTokens() -> int:
    return _sum_usage("inputTokens")


def getTotalOutputTokens() -> int:
    return _sum_usage("outputTokens")


def getTotalCacheReadInputTokens() -> int:
    return _sum_usage("cacheReadInputTokens")


def getTotalCacheCreationInputTokens() -> int:
    return _sum_usage("cacheCreationInputTokens")


def getTotalWebSearchRequests() -> int:
    return _sum_usage("webSearchRequests")


def getTurnOutputTokens() -> int:
    return getTotalOutputTokens() - _output_tokens_at_turn_start


def getCurrentTurnTokenBudget() -> Optional[int]:
    return _current_turn_token_budget


def snapshotOutputTokensForTurn(budget: Optional[int]) -> None:
    global _output_tokens_at_turn_start, _current_turn_token_budget, _budget_continuation_count
    _output_tokens_at_turn_start = getTotalOutputTokens()
    _current_turn_token_budget = budget
    _budget_continuation_count = 0


def getBudgetContinuationCount() -> int:
    return _budget_continuation_count


def incrementBudgetContinuationCount() -> None:
    global _budget_continuation_count
    _budget_continuation_count += 1


# ---------------------------------------------------------------------------
# Model cost / usage
# ---------------------------------------------------------------------------

def setHasUnknownModelCost() -> None:
    _STATE["hasUnknownModelCost"] = True


def hasUnknownModelCost() -> bool:
    return _STATE["hasUnknownModelCost"]


def getLastMainRequestId() -> Optional[str]:
    return _STATE["lastMainRequestId"]


def setLastMainRequestId(request_id: str) -> None:
    _STATE["lastMainRequestId"] = request_id


def getLastApiCompletionTimestamp() -> Optional[int]:
    return _STATE["lastApiCompletionTimestamp"]


def setLastApiCompletionTimestamp(timestamp: int) -> None:
    _STATE["lastApiCompletionTimestamp"] = timestamp


def markPostCompaction() -> None:
    _STATE["pendingPostCompaction"] = True


def consumePostCompaction() -> bool:
    was = _STATE["pendingPostCompaction"]
    _STATE["pendingPostCompaction"] = False
    return was


# ---------------------------------------------------------------------------
# Model usage
# ---------------------------------------------------------------------------

def getModelUsage() -> Dict[str, ModelUsage]:
    return _STATE["modelUsage"]


def getUsageForModel(model: str) -> Optional[ModelUsage]:
    return _STATE["modelUsage"].get(model)


def getMainLoopModelOverride() -> Optional[ModelSetting]:
    return _STATE["mainLoopModelOverride"]


def getInitialMainLoopModel() -> Optional[ModelSetting]:
    return _STATE["initialMainLoopModel"]


def setMainLoopModelOverride(model: Optional[ModelSetting]) -> None:
    _STATE["mainLoopModelOverride"] = model


def setInitialMainLoopModel(model: ModelSetting) -> None:
    _STATE["initialMainLoopModel"] = model


def getSdkBetas() -> Optional[List[str]]:
    return _STATE["sdkBetas"]


def setSdkBetas(betas: Optional[List[str]]) -> None:
    _STATE["sdkBetas"] = betas


# ---------------------------------------------------------------------------
# Cost state reset / restore
# ---------------------------------------------------------------------------

def resetCostState() -> None:
    _STATE["totalCostUSD"] = 0.0
    _STATE["totalAPIDuration"] = 0
    _STATE["totalAPIDurationWithoutRetries"] = 0
    _STATE["totalToolDuration"] = 0
    _STATE["startTime"] = int(time.time() * 1000)
    _STATE["totalLinesAdded"] = 0
    _STATE["totalLinesRemoved"] = 0
    _STATE["hasUnknownModelCost"] = False
    _STATE["modelUsage"] = {}
    _STATE["promptId"] = None


def setCostStateForRestore(
    total_cost_usd: float,
    total_api_duration: int,
    total_api_duration_without_retries: int,
    total_tool_duration: int,
    total_lines_added: int,
    total_lines_removed: int,
    last_duration: Optional[int] = None,
    model_usage: Optional[Dict[str, ModelUsage]] = None,
) -> None:
    _STATE["totalCostUSD"] = total_cost_usd
    _STATE["totalAPIDuration"] = total_api_duration
    _STATE["totalAPIDurationWithoutRetries"] = total_api_duration_without_retries
    _STATE["totalToolDuration"] = total_tool_duration
    _STATE["totalLinesAdded"] = total_lines_added
    _STATE["totalLinesRemoved"] = total_lines_removed
    if model_usage:
        _STATE["modelUsage"] = model_usage
    if last_duration:
        _STATE["startTime"] = int(time.time() * 1000) - last_duration


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def resetStateForTests() -> None:
    if os.environ.get("NODE_ENV") not in ("test",) and os.environ.get("PYTEST_CURRENT_TEST") is None:
        raise RuntimeError("resetStateForTests can only be called in tests")
    global _output_tokens_at_turn_start, _current_turn_token_budget, _budget_continuation_count
    fresh = _get_initial_state()
    _STATE.clear()
    _STATE.update(fresh)
    _output_tokens_at_turn_start = 0
    _current_turn_token_budget = None
    _budget_continuation_count = 0
    _session_switched.clear()


# ---------------------------------------------------------------------------
# Model strings
# ---------------------------------------------------------------------------

def getModelStrings() -> Optional[ModelStrings]:
    return _STATE["modelStrings"]


def setModelStrings(model_strings: ModelStrings) -> None:
    _STATE["modelStrings"] = model_strings


def resetModelStringsForTestingOnly() -> None:
    _STATE["modelStrings"] = None


# ---------------------------------------------------------------------------
# Telemetry / meters
# ---------------------------------------------------------------------------

def setMeter(meter: Any, create_counter: Callable) -> None:
    _STATE["meter"] = meter
    _STATE["sessionCounter"] = create_counter("vivian_code.session.count", {"description": "Count of CLI sessions started"})
    _STATE["locCounter"] = create_counter("vivian_code.lines_of_code.count", {"description": "Count of lines of code modified"})
    _STATE["prCounter"] = create_counter("vivian_code.pull_request.count", {"description": "Number of pull requests created"})
    _STATE["commitCounter"] = create_counter("vivian_code.commit.count", {"description": "Number of git commits created"})
    _STATE["costCounter"] = create_counter("vivian_code.cost.usage", {"description": "Cost of the vivian Code session", "unit": "USD"})
    _STATE["tokenCounter"] = create_counter("vivian_code.token.usage", {"description": "Number of tokens used", "unit": "tokens"})
    _STATE["codeEditToolDecisionCounter"] = create_counter("vivian_code.code_edit_tool.decision", {"description": "Count of code editing tool permission decisions"})
    _STATE["activeTimeCounter"] = create_counter("vivian_code.active_time.total", {"description": "Total active time in seconds", "unit": "s"})


def getMeter() -> Optional[Any]:
    return _STATE["meter"]


def getSessionCounter() -> Optional[Any]:
    return _STATE["sessionCounter"]


def getLocCounter() -> Optional[Any]:
    return _STATE["locCounter"]


def getPrCounter() -> Optional[Any]:
    return _STATE["prCounter"]


def getCommitCounter() -> Optional[Any]:
    return _STATE["commitCounter"]


def getCostCounter() -> Optional[Any]:
    return _STATE["costCounter"]


def getTokenCounter() -> Optional[Any]:
    return _STATE["tokenCounter"]


def getCodeEditToolDecisionCounter() -> Optional[Any]:
    return _STATE["codeEditToolDecisionCounter"]


def getActiveTimeCounter() -> Optional[Any]:
    return _STATE["activeTimeCounter"]


def getLoggerProvider() -> Optional[Any]:
    return _STATE["loggerProvider"]


def setLoggerProvider(provider: Optional[Any]) -> None:
    _STATE["loggerProvider"] = provider


def getEventLogger() -> Optional[Any]:
    return _STATE["eventLogger"]


def setEventLogger(logger: Optional[Any]) -> None:
    _STATE["eventLogger"] = logger


def getMeterProvider() -> Optional[Any]:
    return _STATE["meterProvider"]


def setMeterProvider(provider: Optional[Any]) -> None:
    _STATE["meterProvider"] = provider


def getTracerProvider() -> Optional[Any]:
    return _STATE["tracerProvider"]


def setTracerProvider(provider: Optional[Any]) -> None:
    _STATE["tracerProvider"] = provider


# ---------------------------------------------------------------------------
# Session flags
# ---------------------------------------------------------------------------

def getIsNonInteractiveSession() -> bool:
    return not _STATE["isInteractive"]


def getIsInteractive() -> bool:
    return _STATE["isInteractive"]


def setIsInteractive(value: bool) -> None:
    _STATE["isInteractive"] = value


def getClientType() -> str:
    return _STATE["clientType"]


def setClientType(t: str) -> None:
    _STATE["clientType"] = t


def getSdkAgentProgressSummariesEnabled() -> bool:
    return _STATE["sdkAgentProgressSummariesEnabled"]


def setSdkAgentProgressSummariesEnabled(value: bool) -> None:
    _STATE["sdkAgentProgressSummariesEnabled"] = value


def getKairosActive() -> bool:
    return _STATE["kairosActive"]


def setKairosActive(value: bool) -> None:
    _STATE["kairosActive"] = value


def getStrictToolResultPairing() -> bool:
    return _STATE["strictToolResultPairing"]


def setStrictToolResultPairing(value: bool) -> None:
    _STATE["strictToolResultPairing"] = value


def getUserMsgOptIn() -> bool:
    return _STATE["userMsgOptIn"]


def setUserMsgOptIn(value: bool) -> None:
    _STATE["userMsgOptIn"] = value


def getSessionSource() -> Optional[str]:
    return _STATE["sessionSource"]


def setSessionSource(source: str) -> None:
    _STATE["sessionSource"] = source


def getQuestionPreviewFormat() -> Optional[str]:
    return _STATE["questionPreviewFormat"]


def setQuestionPreviewFormat(fmt: str) -> None:
    _STATE["questionPreviewFormat"] = fmt


def getAgentColorMap() -> Dict[str, AgentColorName]:
    return _STATE["agentColorMap"]


def getFlagSettingsPath() -> Optional[str]:
    return _STATE["flagSettingsPath"]


def setFlagSettingsPath(path: Optional[str]) -> None:
    _STATE["flagSettingsPath"] = path


def getFlagSettingsInline() -> Optional[Dict[str, Any]]:
    return _STATE["flagSettingsInline"]


def setFlagSettingsInline(settings: Optional[Dict[str, Any]]) -> None:
    _STATE["flagSettingsInline"] = settings


def getSessionIngressToken() -> Optional[str]:
    return _STATE["sessionIngressToken"]


def setSessionIngressToken(token: Optional[str]) -> None:
    _STATE["sessionIngressToken"] = token


def getOauthTokenFromFd() -> Optional[str]:
    return _STATE["oauthTokenFromFd"]


def setOauthTokenFromFd(token: Optional[str]) -> None:
    _STATE["oauthTokenFromFd"] = token


def getApiKeyFromFd() -> Optional[str]:
    return _STATE["apiKeyFromFd"]


def setApiKeyFromFd(key: Optional[str]) -> None:
    _STATE["apiKeyFromFd"] = key


def setLastAPIRequest(params: Optional[Any]) -> None:
    _STATE["lastAPIRequest"] = params


def getLastAPIRequest() -> Optional[Any]:
    return _STATE["lastAPIRequest"]


def setLastAPIRequestMessages(messages: Optional[Any]) -> None:
    _STATE["lastAPIRequestMessages"] = messages


def getLastAPIRequestMessages() -> Optional[Any]:
    return _STATE["lastAPIRequestMessages"]


def setLastClassifierRequests(requests: Optional[List[Any]]) -> None:
    _STATE["lastClassifierRequests"] = requests


def getLastClassifierRequests() -> Optional[List[Any]]:
    return _STATE["lastClassifierRequests"]


def setCachedvivianMdContent(content: Optional[str]) -> None:
    _STATE["cachedvivianMdContent"] = content


def getCachedvivianMdContent() -> Optional[str]:
    return _STATE["cachedvivianMdContent"]


def addToInMemoryErrorLog(error_info: Dict[str, str]) -> None:
    MAX_IN_MEMORY_ERRORS = 100
    if len(_STATE["inMemoryErrorLog"]) >= MAX_IN_MEMORY_ERRORS:
        _STATE["inMemoryErrorLog"].pop(0)
    _STATE["inMemoryErrorLog"].append(error_info)


def getAllowedSettingSources() -> List[SettingSource]:
    return _STATE["allowedSettingSources"]


def setAllowedSettingSources(sources: List[SettingSource]) -> None:
    _STATE["allowedSettingSources"] = sources


def preferThirdPartyAuthentication() -> bool:
    return getIsNonInteractiveSession() and _STATE["clientType"] != "vivian-vscode"


def setInlinePlugins(plugins: List[str]) -> None:
    _STATE["inlinePlugins"] = plugins


def getInlinePlugins() -> List[str]:
    return _STATE["inlinePlugins"]


def setChromeFlagOverride(value: Optional[bool]) -> None:
    _STATE["chromeFlagOverride"] = value


def getChromeFlagOverride() -> Optional[bool]:
    return _STATE["chromeFlagOverride"]


def setUseCoworkPlugins(value: bool) -> None:
    _STATE["useCoworkPlugins"] = value


def getUseCoworkPlugins() -> bool:
    return _STATE["useCoworkPlugins"]


def setSessionBypassPermissionsMode(enabled: bool) -> None:
    _STATE["sessionBypassPermissionsMode"] = enabled


def getSessionBypassPermissionsMode() -> bool:
    return _STATE["sessionBypassPermissionsMode"]


def setScheduledTasksEnabled(enabled: bool) -> None:
    _STATE["scheduledTasksEnabled"] = enabled


def getScheduledTasksEnabled() -> bool:
    return _STATE["scheduledTasksEnabled"]


def getSessionCronTasks() -> List[SessionCronTask]:
    return _STATE["sessionCronTasks"]


def addSessionCronTask(task: SessionCronTask) -> None:
    _STATE["sessionCronTasks"].append(task)


def removeSessionCronTasks(ids: List[str]) -> int:
    if not ids:
        return 0
    id_set = set(ids)
    remaining = [t for t in _STATE["sessionCronTasks"] if t.get("id") not in id_set]
    removed = len(_STATE["sessionCronTasks"]) - len(remaining)
    if removed == 0:
        return 0
    _STATE["sessionCronTasks"] = remaining
    return removed


def setSessionTrustAccepted(accepted: bool) -> None:
    _STATE["sessionTrustAccepted"] = accepted


def getSessionTrustAccepted() -> bool:
    return _STATE["sessionTrustAccepted"]


def setSessionPersistenceDisabled(disabled: bool) -> None:
    _STATE["sessionPersistenceDisabled"] = disabled


def isSessionPersistenceDisabled() -> bool:
    return _STATE["sessionPersistenceDisabled"]


def hasExitedPlanModeInSession() -> bool:
    return _STATE["hasExitedPlanMode"]


def setHasExitedPlanMode(value: bool) -> None:
    _STATE["hasExitedPlanMode"] = value


def needsPlanModeExitAttachment() -> bool:
    return _STATE["needsPlanModeExitAttachment"]


def setNeedsPlanModeExitAttachment(value: bool) -> None:
    _STATE["needsPlanModeExitAttachment"] = value


def handlePlanModeTransition(from_mode: str, to_mode: str) -> None:
    if to_mode == "plan" and from_mode != "plan":
        _STATE["needsPlanModeExitAttachment"] = False
    if from_mode == "plan" and to_mode != "plan":
        _STATE["needsPlanModeExitAttachment"] = True


def needsAutoModeExitAttachment() -> bool:
    return _STATE["needsAutoModeExitAttachment"]


def setNeedsAutoModeExitAttachment(value: bool) -> None:
    _STATE["needsAutoModeExitAttachment"] = value


def handleAutoModeTransition(from_mode: str, to_mode: str) -> None:
    if (from_mode == "auto" and to_mode == "plan") or (from_mode == "plan" and to_mode == "auto"):
        return
    from_is_auto = from_mode == "auto"
    to_is_auto = to_mode == "auto"
    if to_is_auto and not from_is_auto:
        _STATE["needsAutoModeExitAttachment"] = False
    if from_is_auto and not to_is_auto:
        _STATE["needsAutoModeExitAttachment"] = True


def hasShownLspRecommendationThisSession() -> bool:
    return _STATE["lspRecommendationShownThisSession"]


def setLspRecommendationShownThisSession(value: bool) -> None:
    _STATE["lspRecommendationShownThisSession"] = value


def setInitJsonSchema(schema: Dict[str, Any]) -> None:
    _STATE["initJsonSchema"] = schema


def getInitJsonSchema() -> Optional[Dict[str, Any]]:
    return _STATE["initJsonSchema"]


def registerHookCallbacks(hooks: Dict[str, List[Any]]) -> None:
    if _STATE["registeredHooks"] is None:
        _STATE["registeredHooks"] = {}
    for event, matchers in hooks.items():
        if event not in _STATE["registeredHooks"]:
            _STATE["registeredHooks"][event] = []
        _STATE["registeredHooks"][event].extend(matchers)


def getRegisteredHooks() -> Optional[Dict[str, List[Any]]]:
    return _STATE["registeredHooks"]


def clearRegisteredHooks() -> None:
    _STATE["registeredHooks"] = None


def clearRegisteredPluginHooks() -> None:
    if not _STATE["registeredHooks"]:
        return
    filtered = {}
    for event, matchers in _STATE["registeredHooks"].items():
        callback_hooks = [m for m in matchers if "pluginRoot" not in m]
        if callback_hooks:
            filtered[event] = callback_hooks
    _STATE["registeredHooks"] = filtered if filtered else None


def resetSdkInitState() -> None:
    _STATE["initJsonSchema"] = None
    _STATE["registeredHooks"] = None


def getPlanSlugCache() -> Dict[str, str]:
    return _STATE["planSlugCache"]


def getSessionCreatedTeams() -> Set[str]:
    return _STATE["sessionCreatedTeams"]


# ---------------------------------------------------------------------------
# Teleported session tracking
# ---------------------------------------------------------------------------

def setTeleportedSessionInfo(info: Dict[str, Any]) -> None:
    _STATE["teleportedSessionInfo"] = {
        "isTeleported": True,
        "hasLoggedFirstMessage": False,
        "sessionId": info.get("sessionId"),
    }


def getTeleportedSessionInfo() -> Optional[Dict[str, Any]]:
    return _STATE["teleportedSessionInfo"]


def markFirstTeleportMessageLogged() -> None:
    if _STATE["teleportedSessionInfo"]:
        _STATE["teleportedSessionInfo"]["hasLoggedFirstMessage"] = True


# ---------------------------------------------------------------------------
# Invoked skills tracking
# ---------------------------------------------------------------------------

def addInvokedSkill(
    skill_name: str,
    skill_path: str,
    content: str,
    agent_id: Optional[str] = None,
) -> None:
    key = f"{agent_id or ''}:{skill_name}"
    _STATE["invokedSkills"][key] = {
        "skillName": skill_name,
        "skillPath": skill_path,
        "content": content,
        "invokedAt": int(time.time() * 1000),
        "agentId": agent_id,
    }


def getInvokedSkills() -> Dict[str, InvokedSkillInfo]:
    return _STATE["invokedSkills"]


def getInvokedSkillsForAgent(agent_id: Optional[str]) -> Dict[str, InvokedSkillInfo]:
    normalized = agent_id
    return {k: v for k, v in _STATE["invokedSkills"].items() if v.get("agentId") == normalized}


def clearInvokedSkills(preserved_agent_ids: Optional[Set[str]] = None) -> None:
    if not preserved_agent_ids:
        _STATE["invokedSkills"].clear()
        return
    to_delete = [
        k for k, v in _STATE["invokedSkills"].items()
        if v.get("agentId") is None or v.get("agentId") not in preserved_agent_ids
    ]
    for k in to_delete:
        del _STATE["invokedSkills"][k]


def clearInvokedSkillsForAgent(agent_id: str) -> None:
    to_delete = [k for k, v in _STATE["invokedSkills"].items() if v.get("agentId") == agent_id]
    for k in to_delete:
        del _STATE["invokedSkills"][k]


# ---------------------------------------------------------------------------
# Slow operations tracking (ant-only dev tooling)
# ---------------------------------------------------------------------------

_MAX_SLOW_OPERATIONS = 10
_SLOW_OPERATION_TTL_MS = 10000


def addSlowOperation(operation: str, duration_ms: int) -> None:
    if os.environ.get("USER_TYPE") != "ant":
        return
    if "exec" in operation and "vivian-prompt-" in operation:
        return
    now = int(time.time() * 1000)
    _STATE["slowOperations"] = [
        op for op in _STATE["slowOperations"]
        if now - op["timestamp"] < _SLOW_OPERATION_TTL_MS
    ]
    _STATE["slowOperations"].append({"operation": operation, "durationMs": duration_ms, "timestamp": now})
    if len(_STATE["slowOperations"]) > _MAX_SLOW_OPERATIONS:
        _STATE["slowOperations"] = _STATE["slowOperations"][-_MAX_SLOW_OPERATIONS:]


def getSlowOperations() -> List[Dict[str, Any]]:
    if not _STATE["slowOperations"]:
        return []
    now = int(time.time() * 1000)
    fresh = [op for op in _STATE["slowOperations"] if now - op["timestamp"] < _SLOW_OPERATION_TTL_MS]
    if len(fresh) != len(_STATE["slowOperations"]):
        _STATE["slowOperations"] = fresh
    return _STATE["slowOperations"]


# ---------------------------------------------------------------------------
# Agent type / remote mode
# ---------------------------------------------------------------------------

def getMainThreadAgentType() -> Optional[str]:
    return _STATE["mainThreadAgentType"]


def setMainThreadAgentType(agent_type: Optional[str]) -> None:
    _STATE["mainThreadAgentType"] = agent_type


def getIsRemoteMode() -> bool:
    return _STATE["isRemoteMode"]


def setIsRemoteMode(value: bool) -> None:
    _STATE["isRemoteMode"] = value


# ---------------------------------------------------------------------------
# System prompt section cache
# ---------------------------------------------------------------------------

def getSystemPromptSectionCache() -> Dict[str, Optional[str]]:
    return _STATE["systemPromptSectionCache"]


def setSystemPromptSectionCacheEntry(name: str, value: Optional[str]) -> None:
    _STATE["systemPromptSectionCache"][name] = value


def clearSystemPromptSectionState() -> None:
    _STATE["systemPromptSectionCache"].clear()


# ---------------------------------------------------------------------------
# Last emitted date
# ---------------------------------------------------------------------------

def getLastEmittedDate() -> Optional[str]:
    return _STATE["lastEmittedDate"]


def setLastEmittedDate(date: Optional[str]) -> None:
    _STATE["lastEmittedDate"] = date


# ---------------------------------------------------------------------------
# Additional directories for vivian.md
# ---------------------------------------------------------------------------

def getAdditionalDirectoriesForvivianMd() -> List[str]:
    return _STATE["additionalDirectoriesForvivianMd"]


def setAdditionalDirectoriesForvivianMd(directories: List[str]) -> None:
    _STATE["additionalDirectoriesForvivianMd"] = directories


# ---------------------------------------------------------------------------
# Channel allowlist
# ---------------------------------------------------------------------------

def getAllowedChannels() -> List[ChannelEntry]:
    return _STATE["allowedChannels"]


def setAllowedChannels(entries: List[ChannelEntry]) -> None:
    _STATE["allowedChannels"] = entries


def getHasDevChannels() -> bool:
    return _STATE["hasDevChannels"]


def setHasDevChannels(value: bool) -> None:
    _STATE["hasDevChannels"] = value


# ---------------------------------------------------------------------------
# Prompt cache state
# ---------------------------------------------------------------------------

def getPromptCache1hAllowlist() -> Optional[List[str]]:
    return _STATE["promptCache1hAllowlist"]


def setPromptCache1hAllowlist(allowlist: Optional[List[str]]) -> None:
    _STATE["promptCache1hAllowlist"] = allowlist


def getPromptCache1hEligible() -> Optional[bool]:
    return _STATE["promptCache1hEligible"]


def setPromptCache1hEligible(eligible: Optional[bool]) -> None:
    _STATE["promptCache1hEligible"] = eligible


# ---------------------------------------------------------------------------
# Beta header latches
# ---------------------------------------------------------------------------

def getAfkModeHeaderLatched() -> Optional[bool]:
    return _STATE["afkModeHeaderLatched"]


def setAfkModeHeaderLatched(v: bool) -> None:
    _STATE["afkModeHeaderLatched"] = v


def getFastModeHeaderLatched() -> Optional[bool]:
    return _STATE["fastModeHeaderLatched"]


def setFastModeHeaderLatched(v: bool) -> None:
    _STATE["fastModeHeaderLatched"] = v


def getCacheEditingHeaderLatched() -> Optional[bool]:
    return _STATE["cacheEditingHeaderLatched"]


def setCacheEditingHeaderLatched(v: bool) -> None:
    _STATE["cacheEditingHeaderLatched"] = v


def getThinkingClearLatched() -> Optional[bool]:
    return _STATE["thinkingClearLatched"]


def setThinkingClearLatched(v: bool) -> None:
    _STATE["thinkingClearLatched"] = v


def clearBetaHeaderLatches() -> None:
    _STATE["afkModeHeaderLatched"] = None
    _STATE["fastModeHeaderLatched"] = None
    _STATE["cacheEditingHeaderLatched"] = None
    _STATE["thinkingClearLatched"] = None


# ---------------------------------------------------------------------------
# Prompt ID
# ---------------------------------------------------------------------------

def getPromptId() -> Optional[str]:
    return _STATE["promptId"]


def setPromptId(id_: Optional[str]) -> None:
    _STATE["promptId"] = id_


# ---------------------------------------------------------------------------
# Scroll drain (ephemeral, not in STATE)
# ---------------------------------------------------------------------------

def markScrollActivity() -> None:
    import threading
    global _scroll_draining, _scroll_drain_timer

    _scroll_draining = True
    if _scroll_drain_timer:
        _scroll_drain_timer.cancel()

    def _clear():
        global _scroll_draining, _scroll_drain_timer
        _scroll_draining = False
        _scroll_drain_timer = None

    t = threading.Timer(_SCROLL_DRAIN_IDLE_MS / 1000.0, _clear)
    t.daemon = True
    t.start()
    _scroll_drain_timer = t


def getIsScrollDraining() -> bool:
    return _scroll_draining


async def waitForScrollIdle() -> None:
    import asyncio
    while _scroll_draining:
        await asyncio.sleep(_SCROLL_DRAIN_IDLE_MS / 1000.0)

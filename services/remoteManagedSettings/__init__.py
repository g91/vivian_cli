"""Remote managed settings package."""
from .index import (
    initializeRemoteManagedSettingsLoadingPromise,
    computeChecksumFromSettings,
    isEligibleForRemoteManagedSettings,
    waitForRemoteManagedSettingsToLoad,
    clearRemoteManagedSettingsCache,
    loadRemoteManagedSettings,
    refreshRemoteManagedSettings,
    startBackgroundPolling,
    stopBackgroundPolling,
)
from .securityCheck import (
    SecurityCheckResult,
    checkManagedSettingsSecurity,
    handleSecurityCheckResult,
)
from .syncCache import isRemoteManagedSettingsEligible, resetSyncCache
from .syncCacheState import (
    getRemoteManagedSettingsSyncFromCache,
    getSettingsPath,
    resetSyncCache as resetRemoteManagedSettingsSyncState,
    setEligibility,
    setSessionCache,
)
from .types import RemoteManagedSettingsFetchResult, RemoteManagedSettingsResponse

__all__ = [
    "SecurityCheckResult",
    "RemoteManagedSettingsFetchResult",
    "RemoteManagedSettingsResponse",
    "checkManagedSettingsSecurity",
    "getRemoteManagedSettingsSyncFromCache",
    "getSettingsPath",
    "handleSecurityCheckResult",
    "initializeRemoteManagedSettingsLoadingPromise",
    "computeChecksumFromSettings",
    "isEligibleForRemoteManagedSettings",
    "isRemoteManagedSettingsEligible",
    "loadRemoteManagedSettings",
    "refreshRemoteManagedSettings",
    "resetRemoteManagedSettingsSyncState",
    "resetSyncCache",
    "setEligibility",
    "setSessionCache",
    "startBackgroundPolling",
    "stopBackgroundPolling",
    "waitForRemoteManagedSettingsToLoad",
    "clearRemoteManagedSettingsCache",
]

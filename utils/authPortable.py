"""Port of src/utils/authPortable.ts."""
from __future__ import annotations

import asyncio


async def maybeRemoveApiKeyFromMacOSKeychainThrows():
    if asyncio.get_running_loop() is None:
        return None
    if __import__("sys").platform != "darwin":
        return None

    try:
        from .secureStorage.macOsKeychainHelpers import getMacOsKeychainStorageServiceName
        service_name = getMacOsKeychainStorageServiceName() or "vivian-code-credentials"
    except Exception:
        service_name = "vivian-code-credentials"

    from .execFileNoThrow import exec_file_no_throw

    result = await exec_file_no_throw(
        "security",
        ["delete-generic-password", "-a", __import__("os").environ.get("USER", ""), "-s", service_name],
    )
    if result.get("code") != 0:
        raise RuntimeError("Failed to delete keychain entry")
    return None


def normalizeApiKeyForConfig(apiKey):
    if not isinstance(apiKey, str):
        return apiKey
    return apiKey[-20:]


maybe_remove_api_key_from_mac_os_keychain_throws = maybeRemoveApiKeyFromMacOSKeychainThrows
normalize_api_key_for_config = normalizeApiKeyForConfig


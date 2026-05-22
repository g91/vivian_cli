"""
Port of src/utils/plugins/mcpbHandler.ts

MCPB file handler - loads .mcpb/.dxt files.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import zipfile
from typing import Any, Dict, List, Optional

from ..debug import logForDebugging
from ..errors import errorMessage, isENOENT
from ..log import logError
from ..slowOperations import json_parse, json_stringify
from ..secureStorage import getSecureStorage
from ..settings.settings import getSettings_DEPRECATED, updateSettingsForSource

UserConfigValues = Dict[str, Any]
UserConfigSchema = Dict[str, Any]
McpbLoadResult = Dict[str, Any]
McpbNeedsConfigResult = Dict[str, Any]
McpbCacheMetadata = Dict[str, Any]
ProgressCallback = Any


def isMcpbSource(source: str) -> bool:
    return source.endswith(".mcpb") or source.endswith(".dxt")


def _is_url(source: str) -> bool:
    return source.startswith("http://") or source.startswith("https://")


def _generate_content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def _get_mcpb_cache_dir(plugin_path: str) -> str:
    return os.path.join(plugin_path, ".mcpb-cache")


def _get_metadata_path(cache_dir: str, source: str) -> str:
    source_hash = hashlib.md5(source.encode()).hexdigest()[:8]
    return os.path.join(cache_dir, f"{source_hash}.metadata.json")


def _server_secrets_key(plugin_id: str, server_name: str) -> str:
    return f"{plugin_id}/{server_name}"


def loadMcpServerUserConfig(plugin_id: str, server_name: str) -> Optional[UserConfigValues]:
    try:
        settings = getSettings_DEPRECATED()
        non_sensitive = settings.get("pluginConfigs", {}).get(plugin_id, {}).get("mcpServers", {}).get(server_name)

        storage = getSecureStorage()
        sensitive = None
        if storage:
            sensitive = storage.read().get("pluginSecrets", {}).get(_server_secrets_key(plugin_id, server_name))

        if not non_sensitive and not sensitive:
            return None
        return {**(non_sensitive or {}), **(sensitive or {})}
    except Exception as e:
        logError(e)
        return None


def saveMcpServerUserConfig(
    plugin_id: str,
    server_name: str,
    config: UserConfigValues,
    schema: UserConfigSchema,
) -> None:
    non_sensitive: Dict[str, Any] = {}
    sensitive: Dict[str, str] = {}

    for key, value in config.items():
        if schema.get(key, {}).get("sensitive") is True:
            sensitive[key] = str(value)
        else:
            non_sensitive[key] = value

    # Write sensitive to secureStorage
    storage = getSecureStorage()
    if storage and sensitive:
        existing = storage.read() or {}
        if "pluginSecrets" not in existing:
            existing["pluginSecrets"] = {}
        existing["pluginSecrets"][_server_secrets_key(plugin_id, server_name)] = sensitive
        storage.update(existing)

    # Write non-sensitive to settings
    if non_sensitive:
        settings = getSettings_DEPRECATED()
        if "pluginConfigs" not in settings:
            settings["pluginConfigs"] = {}
        if plugin_id not in settings["pluginConfigs"]:
            settings["pluginConfigs"][plugin_id] = {}
        if "mcpServers" not in settings["pluginConfigs"][plugin_id]:
            settings["pluginConfigs"][plugin_id]["mcpServers"] = {}
        settings["pluginConfigs"][plugin_id]["mcpServers"][server_name] = non_sensitive
        updateSettingsForSource("userSettings", settings)


def validateUserConfig(
    values: UserConfigValues,
    schema: UserConfigSchema,
) -> Dict[str, Any]:
    errors: List[str] = []
    for key, field_schema in schema.items():
        if field_schema.get("required") and key not in values:
            errors.append(f"Missing required field: {key}")
        if key in values:
            val = values[key]
            expected_type = field_schema.get("type", "string")
            if expected_type == "string" and not isinstance(val, str):
                errors.append(f"Field '{key}' must be a string")
            elif expected_type == "number" and not isinstance(val, (int, float)):
                errors.append(f"Field '{key}' must be a number")
            elif expected_type == "boolean" and not isinstance(val, bool):
                errors.append(f"Field '{key}' must be a boolean")
    return {"valid": len(errors) == 0, "errors": errors}


async def loadMcpbFile(
    source: str,
    plugin_path: str,
    plugin_id: str,
    on_progress: Optional[Any] = None,
    provided_user_config: Optional[UserConfigValues] = None,
    force_config_dialog: bool = False,
) -> Dict[str, Any]:
    cache_dir = _get_mcpb_cache_dir(plugin_path)
    os.makedirs(cache_dir, exist_ok=True)

    # Check cache
    metadata = await _load_cache_metadata(cache_dir, source)
    if metadata and not await _check_mcpb_changed(source, plugin_path):
        return {"manifest": {}, "mcpConfig": {}, "extractedPath": metadata.get("extractedPath", ""), "contentHash": metadata.get("contentHash", "")}

    # Download/load MCPB
    if _is_url(source):
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(source)
            mcpb_data = resp.content
    else:
        with open(source, "rb") as f:
            mcpb_data = f.read()

    content_hash = _generate_content_hash(mcpb_data)
    extract_path = os.path.join(cache_dir, content_hash)

    # Extract ZIP
    os.makedirs(extract_path, exist_ok=True)
    import io
    with zipfile.ZipFile(io.BytesIO(mcpb_data), "r") as zf:
        zf.extractall(extract_path)

    # Read manifest
    manifest_path = os.path.join(extract_path, "manifest.json")
    manifest: Dict[str, Any] = {}
    if os.path.isfile(manifest_path):
        with open(manifest_path, "r") as f:
            manifest = json.loads(f.read())

    # Save cache metadata
    new_metadata: McpbCacheMetadata = {
        "source": source,
        "contentHash": content_hash,
        "extractedPath": extract_path,
        "cachedAt": "",  # ISO timestamp would go here
        "lastChecked": "",
    }
    await _save_cache_metadata(cache_dir, source, new_metadata)

    return {"manifest": manifest, "mcpConfig": {}, "extractedPath": extract_path, "contentHash": content_hash}


async def _load_cache_metadata(cache_dir: str, source: str) -> Optional[McpbCacheMetadata]:
    path = _get_metadata_path(cache_dir, source)
    try:
        if os.path.isfile(path):
            with open(path, "r") as f:
                return json.loads(f.read())
    except Exception:
        pass
    return None


async def _save_cache_metadata(cache_dir: str, source: str, metadata: McpbCacheMetadata) -> None:
    path = _get_metadata_path(cache_dir, source)
    os.makedirs(cache_dir, exist_ok=True)
    with open(path, "w") as f:
        json.dump(metadata, f, indent=2)


async def _check_mcpb_changed(source: str, plugin_path: str) -> bool:
    return False


"""
Port of src/utils/plugins/validatePlugin.ts

Plugin validation utilities.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from ..debug import logForDebugging
from ..errors import errorMessage, getErrnoCode

MARKETPLACE_ONLY_MANIFEST_FIELDS = {"category", "source", "tags", "strict", "id"}
FRONTMATTER_REGEX = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

ValidationResult = Dict[str, Any]
ValidationError = Dict[str, Any]
ValidationWarning = Dict[str, Any]


def _detect_manifest_type(file_path: str) -> str:
    file_name = os.path.basename(file_path)
    dir_name = os.path.basename(os.path.dirname(file_path))
    if file_name == "plugin.json":
        return "plugin"
    if file_name == "marketplace.json":
        return "marketplace"
    if dir_name == ".vivian-plugin":
        return "plugin"
    return "unknown"


def _format_zod_errors(errors: List[Dict[str, Any]]) -> List[ValidationError]:
    return [
        {"path": ".".join(str(p) for p in e.get("path", [])), "message": e.get("message", ""), "code": e.get("code")}
        for e in errors
    ]


def _check_path_traversal(path: str, field: str, errors: List[ValidationError], hint: Optional[str] = None) -> None:
    if ".." in path:
        msg = f'Path contains "..": {path}. {hint}' if hint else f'Path contains ".." which could be a path traversal attempt: {path}'
        errors.append({"path": field, "message": msg})


async def validatePluginManifest(file_path: str) -> ValidationResult:
    errors: List[ValidationError] = []
    warnings: List[ValidationWarning] = []
    absolute_path = os.path.abspath(file_path)

    try:
        with open(absolute_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return {"success": False, "errors": [{"path": "file", "message": f"File not found: {absolute_path}"}], "warnings": [], "filePath": absolute_path, "fileType": "plugin"}
    except IsADirectoryError:
        return {"success": False, "errors": [{"path": "file", "message": f"Is a directory: {absolute_path}"}], "warnings": [], "filePath": absolute_path, "fileType": "plugin"}
    except Exception as e:
        return {"success": False, "errors": [{"path": "file", "message": str(e)}], "warnings": [], "filePath": absolute_path, "fileType": "plugin"}

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        return {"success": False, "errors": [{"path": "json", "message": f"Invalid JSON: {e}"}], "warnings": [], "filePath": absolute_path, "fileType": "plugin"}

    if isinstance(parsed, dict):
        # Check commands paths
        for cmd_path in (parsed.get("commands") or []):
            if isinstance(cmd_path, str):
                _check_path_traversal(cmd_path, "commands", errors)
        for agent_path in (parsed.get("agents") or []):
            if isinstance(agent_path, str):
                _check_path_traversal(agent_path, "agents", errors)
        for skill_path in (parsed.get("skills") or []):
            if isinstance(skill_path, str):
                _check_path_traversal(skill_path, "skills", errors)

        # Warn about marketplace-only fields
        for field in MARKETPLACE_ONLY_MANIFEST_FIELDS:
            if field in parsed:
                warnings.append({"path": field, "message": f"Field '{field}' belongs in marketplace.json, not plugin.json"})

    # Basic required field checks
    if isinstance(parsed, dict):
        if not parsed.get("name"):
            errors.append({"path": "name", "message": "Missing required field: name"})
        if not parsed.get("version"):
            warnings.append({"path": "version", "message": "Missing version field"})

    return {"success": len(errors) == 0, "errors": errors, "warnings": warnings, "filePath": absolute_path, "fileType": "plugin"}


async def validateMarketplaceManifest(file_path: str) -> ValidationResult:
    errors: List[ValidationError] = []
    warnings: List[ValidationWarning] = []
    absolute_path = os.path.abspath(file_path)

    try:
        with open(absolute_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return {"success": False, "errors": [{"path": "file", "message": f"File not found: {absolute_path}"}], "warnings": [], "filePath": absolute_path, "fileType": "marketplace"}
    except Exception as e:
        return {"success": False, "errors": [{"path": "file", "message": str(e)}], "warnings": [], "filePath": absolute_path, "fileType": "marketplace"}

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        return {"success": False, "errors": [{"path": "json", "message": f"Invalid JSON: {e}"}], "warnings": [], "filePath": absolute_path, "fileType": "marketplace"}

    if isinstance(parsed, dict):
        plugins = parsed.get("plugins", [])
        if isinstance(plugins, list):
            for i, plugin in enumerate(plugins):
                if isinstance(plugin, dict):
                    source = plugin.get("source", "")
                    if isinstance(source, str):
                        _check_path_traversal(source, f"plugins[{i}].source", errors,
                            f'Plugin source paths are resolved relative to the marketplace root. Use "./{source.lstrip("./")}" instead of "{source}".' if ".." in source else None)

    return {"success": len(errors) == 0, "errors": errors, "warnings": warnings, "filePath": absolute_path, "fileType": "marketplace"}


async def validateManifest(file_path: str) -> ValidationResult:
    absolute_path = os.path.abspath(file_path)
    if os.path.isdir(file_path):
        # Validate all manifests in directory
        results: List[ValidationResult] = []
        for root, dirs, files in os.walk(file_path):
            if "plugin.json" in files:
                results.append(await validatePluginManifest(os.path.join(root, "plugin.json")))
            if "marketplace.json" in files:
                results.append(await validateMarketplaceManifest(os.path.join(root, "marketplace.json")))
        if not results:
            return {"success": False, "errors": [{"path": "dir", "message": "No plugin.json or marketplace.json found"}], "warnings": [], "filePath": absolute_path, "fileType": "plugin"}
        return results[0]

    manifest_type = _detect_manifest_type(file_path)
    if manifest_type == "plugin":
        return await validatePluginManifest(file_path)
    elif manifest_type == "marketplace":
        return await validateMarketplaceManifest(file_path)
    return {"success": False, "errors": [{"path": "type", "message": f"Unknown manifest type: {file_path}"}], "warnings": [], "filePath": absolute_path, "fileType": "unknown"}


checkPathTraversal = _check_path_traversal


"""Port of src/utils/dxt/helpers.ts"""
from __future__ import annotations
import json
import re
from typing import Any, Dict, Optional


async def validateManifest(manifestJson: Any) -> Dict[str, Any]:
    """Parses and validates a DXT manifest from a JSON object.

    Lazy-imports schema validation. Raises ValueError if manifest is invalid.
    """
    # Required top-level fields per McpbManifest schema
    required_fields = ['name', 'version', 'description', 'author', 'mcp_version']
    errors = []

    if not isinstance(manifestJson, dict):
        raise ValueError('Invalid manifest: expected JSON object')

    for field in required_fields:
        if field not in manifestJson:
            errors.append(f'{field}: required field missing')

    # Validate author sub-object
    author = manifestJson.get('author', {})
    if not isinstance(author, dict) or not author.get('name'):
        errors.append('author.name: required field missing')

    if errors:
        raise ValueError(f"Invalid manifest: {'; '.join(errors)}")

    return manifestJson


async def parseAndValidateManifestFromText(manifestText: str) -> Dict[str, Any]:
    """Parses and validates a DXT manifest from raw text data."""
    try:
        manifest_json = json.loads(manifestText)
    except Exception as error:
        raise ValueError(f'Invalid JSON in manifest.json: {error}')

    return await validateManifest(manifest_json)


async def parseAndValidateManifestFromBytes(manifestData: bytes) -> Dict[str, Any]:
    """Parses and validates a DXT manifest from raw binary data."""
    manifest_text = manifestData.decode('utf-8')
    return await parseAndValidateManifestFromText(manifest_text)


def generateExtensionId(
    manifest: Dict[str, Any],
    prefix: Optional[str] = None,
) -> str:
    """Generates an extension ID from author name and extension name.
    Uses the same algorithm as the directory backend for consistency.
    """
    def sanitize(s: str) -> str:
        return (
            re.sub(r'-+', '-', re.sub(r'[^a-z0-9-_.]', '', re.sub(r'\s+', '-', s.lower())))
            .strip('-')
        )

    author_name = manifest.get('author', {}).get('name', '')
    extension_name = manifest.get('name', '')

    sanitized_author = sanitize(author_name)
    sanitized_name = sanitize(extension_name)

    if prefix:
        return f'{prefix}.{sanitized_author}.{sanitized_name}'
    return f'{sanitized_author}.{sanitized_name}'

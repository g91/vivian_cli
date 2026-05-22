"""Port of src/utils/settings/schemaOutput.ts"""
from __future__ import annotations
from typing import Dict, Any

SCHEMA_VERSION = '1.0'

SETTINGS_SCHEMA: Dict[str, Any] = {
    '$schema': 'http://json-schema.org/draft-07/schema#',
    'title': 'vivian Code Settings',
    'description': 'Configuration settings for vivian Code CLI',
    'type': 'object',
    'properties': {
        'model': {
            'type': 'string',
            'description': 'The vivian model to use',
        },
        'permissions': {
            'type': 'object',
            'description': 'Permission rules for tool use',
            'properties': {
                'allow': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Rules to always allow without prompting',
                },
                'deny': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Rules to always deny without prompting',
                },
                'ask': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Rules to always ask before allowing',
                },
            },
        },
        'theme': {
            'type': 'string',
            'enum': ['light', 'dark', 'auto'],
            'description': 'UI color theme',
        },
        'verbose': {
            'type': 'boolean',
            'description': 'Enable verbose output',
        },
        'includeCoAuthoredBy': {
            'type': 'boolean',
            'description': 'Include co-authored-by header in git commits',
        },
        'cleanupPeriodDays': {
            'type': 'integer',
            'description': 'Number of days after which to clean up old logs',
        },
        'env': {
            'type': 'object',
            'additionalProperties': {'type': 'string'},
            'description': 'Environment variables to inject into Bash sessions',
        },
        'mcpServers': {
            'type': 'object',
            'description': 'MCP server configurations',
        },
    },
    'additionalProperties': False,
}


def getSettingsSchema() -> Dict[str, Any]:
    """Return the JSON Schema for vivian Code settings."""
    return SCHEMA_VERSION, SETTINGS_SCHEMA


def printSettingsSchema() -> None:
    """Print the settings JSON schema to stdout."""
    import json
    _, schema = getSettingsSchema()
    print(json.dumps(schema, indent=2))

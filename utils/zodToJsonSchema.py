"""
Port of src/utils/zodToJsonSchema.ts
"""
from __future__ import annotations

from typing import Any, Dict
from weakref import WeakKeyDictionary


JsonSchema7Type = Dict[str, Any]
_cache: "WeakKeyDictionary[object, JsonSchema7Type]" = WeakKeyDictionary()


def _coerce_schema(schema: Any) -> JsonSchema7Type:
    if isinstance(schema, dict):
        return schema
    if callable(schema) and not hasattr(schema, 'model_json_schema') and not hasattr(schema, 'json_schema') and not hasattr(schema, 'schema'):
        schema = schema()
        if isinstance(schema, dict):
            return schema
    for attr in ('model_json_schema', 'json_schema', 'schema'):
        method = getattr(schema, attr, None)
        if callable(method):
            value = method()
            if isinstance(value, dict):
                return value
    if hasattr(schema, '__dict__'):
        value = dict(getattr(schema, '__dict__'))
        if value:
            return value
    raise TypeError(f'Unsupported schema type for zodToJsonSchema: {type(schema).__name__}')


def zodToJsonSchema(schema: Any) -> JsonSchema7Type:
    """Converts a Zod v4 schema to JSON Schema format."""
    if isinstance(schema, dict):
        return schema
    try:
        hit = _cache.get(schema)
    except TypeError:
        hit = None
    if hit is not None:
        return hit
    result = _coerce_schema(schema)
    try:
        _cache[schema] = result
    except TypeError:
        pass
    return result


zod_to_json_schema = zodToJsonSchema


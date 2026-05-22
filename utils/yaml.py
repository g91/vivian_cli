"""YAML utilities — mirrors src/utils/yaml.ts"""
from __future__ import annotations

from typing import Any


def parse_yaml(input: str) -> Any:
    """Parse a YAML string. Requires PyYAML."""
    try:
        import yaml  # type: ignore[import]
        return yaml.safe_load(input)
    except ImportError:
        # Fallback: try JSON (YAML is a superset of JSON)
        import json
        return json.loads(input)


def stringify_yaml(value: Any, **kwargs) -> str:
    """Serialize a value to YAML string."""
    try:
        import yaml  # type: ignore[import]
        return yaml.dump(value, default_flow_style=False, allow_unicode=True, **kwargs)
    except ImportError:
        import json
        return json.dumps(value, indent=2)

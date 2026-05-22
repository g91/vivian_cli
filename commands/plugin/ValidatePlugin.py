"""ValidatePlugin — mirrors src/commands/plugin/ValidatePlugin.tsx."""
from __future__ import annotations

def validate_plugin(manifest: dict) -> tuple[bool, str]:
    required = ["name", "version", "description"]
    for key in required:
        if key not in manifest:
            return False, f"Missing required field: {key}"
    return True, "Valid"

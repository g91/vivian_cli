"""parseArgs — mirrors src/commands/plugin/parseArgs.ts."""
from __future__ import annotations

def parse_args(args: str) -> dict[str, str]:
    parts = args.strip().split()
    result: dict[str, str] = {}
    i = 0
    while i < len(parts):
        if parts[i].startswith("--"):
            key = parts[i][2:]
            if i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                result[key] = parts[i + 1]
                i += 2
            else:
                result[key] = "true"
                i += 1
        else:
            result[f"arg{i}"] = parts[i]
            i += 1
    return result

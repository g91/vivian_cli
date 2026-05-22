"""doctor command — mirrors src/commands/doctor/doctor.tsx.

Runs system diagnostics: API health, model availability, config validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def runDiagnostics(context: CommandContext) -> str:
    """Run system diagnostics."""
    lines = ["╔══════════════════════════════════╗",
             "║        System Diagnostics        ║",
             "╚══════════════════════════════════╝", ""]

    # API health
    client = getattr(context, "client", None)
    try:
        qe = getattr(context, "query_engine", None)
        if client is None and qe is not None:
            client = getattr(qe, "client", None)
    except Exception:
        pass

    try:
        if client is not None and hasattr(client, "health"):
            health = await client.health()
            if isinstance(health, dict):
                lines.append(f"  API health:    {health.get('status', 'unknown')}")
            else:
                lines.append(f"  API health:    {health}")
        else:
            lines.append("  API health:    unavailable")
    except Exception as e:
        lines.append(f"  API health:    ERROR ({e})")

    # Models
    try:
        if client is not None and hasattr(client, "list_models"):
            models = await client.list_models()
            if isinstance(models, list):
                lines.append(f"  Models:        {len(models)} available")
            else:
                lines.append(f"  Models:        {len(models.get('data', []))} available")
        else:
            lines.append("  Models:        unavailable")
    except Exception as e:
        lines.append(f"  Models:        ERROR ({e})")

    # Config
    try:
        cfg = getattr(context, "config", {}) or {}
        lines.append(f"  Config keys:   {len(cfg)}")
    except Exception:
        lines.append("  Config:        unavailable")

    # Python version
    import sys
    lines.append(f"  Python:        {sys.version.split()[0]}")

    # Query engine
    try:
        qe = getattr(context, "query_engine", None)
        if qe:
            msgs = getattr(qe, "messages", []) or []
            lines.append(f"  Messages:      {len(msgs)} in history")
            model = getattr(qe, "model", "") or "unknown"
            lines.append(f"  Active model:  {model}")
    except Exception:
        pass

    return "\n".join(lines)


async def call(args: str, context: CommandContext) -> TextResult:
    """Run diagnostics."""
    from ...types.command import TextResult
    result = await runDiagnostics(context)
    return TextResult(result)


run_diagnostics = runDiagnostics

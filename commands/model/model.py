"""model command — mirrors src/commands/model/model.tsx.

View or switch the active AI model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def getModelInfo(current_model: str, available_models: list | None = None) -> str:
    """Get model information."""
    lines = [f"Current model: {current_model}"]
    if available_models:
        lines.append("")
        lines.append("Available models:")
        for m in available_models[:20]:
            marker = " ← current" if m == current_model else ""
            lines.append(f"  • {m}{marker}")
    return "\n".join(lines)


async def call(args: str, context: CommandContext) -> TextResult:
    """View or switch the active model."""
    from ...types.command import TextResult

    model_name = args.strip() if args else ""

    current = ""
    available: list[str] = []

    try:
        qe = getattr(context, "query_engine", None)
        if qe:
            current = getattr(qe, "model", "") or ""
    except Exception:
        pass

    client = getattr(context, "client", None)
    try:
        qe = getattr(context, "query_engine", None)
        if client is None and qe is not None:
            client = getattr(qe, "client", None)
    except Exception:
        pass

    try:
        if client is not None and hasattr(client, "list_models"):
            models = await client.list_models()
            if isinstance(models, list):
                available = [str(item) for item in models]
            else:
                available = [str(item.get("id", "")) for item in models.get("data", []) if item.get("id")]
    except Exception:
        pass

    if not model_name:
        return TextResult(getModelInfo(current, available))

    # Switch model
    try:
        qe = getattr(context, "query_engine", None)
        if qe:
            qe.model = model_name
    except Exception:
        pass

    try:
        app_state = getattr(context, "app_state", None)
        if app_state:
            app_state.main_loop_model = model_name
    except Exception:
        pass

    try:
        if hasattr(context, "set_setting"):
            context.set_setting("model", model_name)
    except Exception:
        pass

    return TextResult(f"Model set to: {model_name}")


get_model_info = getModelInfo

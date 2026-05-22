"""remote-env command — mirrors src/commands/remote-env/.

Configure remote environment variables for headless/bridge sessions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    """View or configure remote environment."""
    from ...types.command import TextResult
    parts = args.strip().split(maxsplit=1) if args.strip() else []
    action = parts[0].lower() if parts else ""

    if not action or action == "list":
        try:
            env = getattr(context, "config", {}).get("remote_env", {})
            if env:
                lines = ["Remote Environment:", ""]
                for k, v in env.items():
                    lines.append(f"  {k}={v}")
                return TextResult("\n".join(lines))
        except Exception:
            pass
        return TextResult("No remote environment variables set.\nUse /remote-env set KEY=VALUE")

    if action == "set" and len(parts) >= 2:
        kv = parts[1].split("=", 1)
        if len(kv) == 2:
            key, val = kv
            try:
                env = dict(getattr(context, "config", {}).get("remote_env", {}))
                env[key] = val
                if hasattr(context, "set_setting"):
                    context.set_setting("remote_env", env)
            except Exception:
                pass
            return TextResult(f"Remote env set: {key}={val}")
        return TextResult("Format: /remote-env set KEY=VALUE")

    if action == "unset" and len(parts) >= 2:
        key = parts[1]
        try:
            env = dict(getattr(context, "config", {}).get("remote_env", {}))
            if key in env:
                del env[key]
                if hasattr(context, "set_setting"):
                    context.set_setting("remote_env", env)
                return TextResult(f"Remote env unset: {key}")
        except Exception:
            pass
        return TextResult(f"Key not found: {key}")

    return TextResult("Usage: /remote-env [list|set KEY=VALUE|unset KEY]")


showRemoteEnv = call
show_remote_env = call

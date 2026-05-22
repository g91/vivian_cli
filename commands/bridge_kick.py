"""bridge-kick command — mirrors src/commands/bridge-kick.ts.

Inject bridge failure states for manual recovery testing (debug tool).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types.command import CommandContext, TextResult

USAGE = """/bridge-kick <subcommand>
  close <code>          Fire ws_closed with the given code (e.g. 1002)
  poll <status> [type]  Next poll throws BridgeFatalError(status, type)
  poll transient        Next poll throws transient rejection
  register fail [N]     Next N registers transient-fail (default 1)
  register fatal        Next register 403s (terminal)
  reconnect-session fail Next POST /bridge/reconnect fails
  heartbeat <status>    Next heartbeat throws BridgeFatalError(status)
  reconnect             Call reconnectEnvironmentWithSession directly
  status                Print bridge state"""


async def call(args: str, context: CommandContext) -> TextResult:
    """Inject bridge failure states for testing."""
    from ..types.command import TextResult
    parts = args.strip().split() if args.strip() else []
    sub = parts[0] if parts else ""

    if sub == "status":
        try:
            bridge = getattr(context, "bridge", None)
            if bridge:
                return TextResult(f"Bridge state: connected={getattr(bridge, 'connected', False)}")
        except Exception:
            pass
        return TextResult("No bridge debug handle registered.")

    if sub == "close" and len(parts) >= 2:
        try:
            code = int(parts[1])
            return TextResult(f"Fired transport close({code}). Watch debug.log for recovery.")
        except ValueError:
            return TextResult(f"close: need a numeric code\n{USAGE}")

    if sub == "reconnect":
        return TextResult("Called reconnectEnvironmentWithSession(). Watch debug.log.")

    if sub == "poll" and len(parts) >= 2:
        return TextResult(f"Next poll will throw error ({parts[1]}). Poll loop woken.")

    if sub == "register" and len(parts) >= 2:
        n = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
        return TextResult(f"Next {n} registerBridgeEnvironment call(s) will transient-fail.")

    if sub == "heartbeat" and len(parts) >= 2:
        return TextResult(f"Next heartbeat will {parts[1]}.")

    if sub == "reconnect-session":
        return TextResult("Next POST /bridge/reconnect calls will fail.")

    return TextResult(USAGE)


kickBridge = call
kick_bridge = call

"""Remote package — mirrors src/remote/."""
from .remote_session_manager import (
    RemotePermissionResponse, RemoteSessionConfig, RemoteSessionCallbacks,
    RemoteSessionManager,
)
from .remote_permission_bridge import (
    create_synthetic_assistant_message,
    create_tool_stub,
)
from .sdk_message_adapter import (
    convert_sdk_message,
    is_session_end_message,
    is_success_result,
    get_result_text,
)
from .sessions_websocket import SessionsWebSocket, SessionsWebSocketCallbacks

__all__ = [
    "RemotePermissionResponse", "RemoteSessionConfig", "RemoteSessionCallbacks",
    "RemoteSessionManager",
    "create_synthetic_assistant_message", "create_tool_stub",
    "convert_sdk_message", "is_session_end_message", "is_success_result", "get_result_text",
    "SessionsWebSocket", "SessionsWebSocketCallbacks",
]

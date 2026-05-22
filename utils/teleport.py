"""Compatibility shim for the teleport package implementation."""
from __future__ import annotations

from .teleport import (
    checkOutTeleportedSessionBranch,
    createTeleportResumeSystemMessage,
    createTeleportResumeUserMessage,
    fetchFromOrigin,
    getCurrentBranch,
    processMessagesForTeleportResume,
    teleportResumeCodeSession,
    validateGitState,
    validateSessionRepository,
)


create_teleport_resume_system_message = createTeleportResumeSystemMessage
create_teleport_resume_user_message = createTeleportResumeUserMessage
check_out_teleported_session_branch = checkOutTeleportedSessionBranch
process_messages_for_teleport_resume = processMessagesForTeleportResume
teleport_resume_code_session = teleportResumeCodeSession
fetch_from_origin = fetchFromOrigin
get_current_branch_name = getCurrentBranch
validate_git_state = validateGitState
validate_session_repository = validateSessionRepository


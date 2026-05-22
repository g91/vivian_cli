"""Teleport resume — mirrors src/hooks/useTeleportResume.ts."""
from __future__ import annotations

from ..bootstrap.state import setTeleportedSessionInfo
from ..services.analytics.index import logEvent
from ..utils.errors import TeleportOperationError, error_message
from ..utils.teleport import teleportResumeCodeSession


def _build_state() -> dict:
    state = {
        'isResuming': False,
        'error': None,
        'selectedSession': None,
    }

    async def resumeSession(session):
        state['isResuming'] = True
        state['error'] = None
        state['selectedSession'] = session
        session_id = session.get('id') if isinstance(session, dict) else getattr(session, 'id', None)
        logEvent('tengu_teleport_resume_session', {'source': 'localCommand', 'session_id': session_id})
        try:
            result = await teleportResumeCodeSession(session_id)
            setTeleportedSessionInfo({'sessionId': session_id})
            state['isResuming'] = False
            return result
        except Exception as err:
            state['error'] = {
                'message': err.args[0] if isinstance(err, TeleportOperationError) else error_message(err),
                'formattedMessage': err.formatted_message if isinstance(err, TeleportOperationError) else None,
                'isOperationError': isinstance(err, TeleportOperationError),
            }
            state['isResuming'] = False
            return None

    def clearError() -> None:
        state['error'] = None

    state['resumeSession'] = resumeSession
    state['clearError'] = clearError
    return state


async def useTeleportResume(source: str = 'localCommand') -> dict:
    """Resume from teleport."""
    state = _build_state()
    state['source'] = source
    return state

use_teleport_resume = useTeleportResume

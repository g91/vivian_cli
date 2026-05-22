"""
Port of src/utils/sessionIngressAuth.ts
"""
from __future__ import annotations

from typing import Optional
import os

from ..bootstrap.state import getSessionIngressToken, setSessionIngressToken
from .debug import logForDebugging
from .envUtils import is_env_truthy
from .errors import error_message, is_enoent


CCR_TOKEN_DIR = '/home/vivian/.vivian/remote'
CCR_SESSION_INGRESS_TOKEN_PATH = f'{CCR_TOKEN_DIR}/.session_ingress_token'
_token_read_attempted = False


def _read_token_from_well_known_file(path: str, token_name: str) -> Optional[str]:
    try:
        token = open(path, 'r', encoding='utf-8').read().strip()
        if not token:
            return None
        logForDebugging(f'Read {token_name} from well-known file {path}')
        return token
    except Exception as error:
        if not is_enoent(error):
            logForDebugging(
                f'Failed to read {token_name} from {path}: {error_message(error)}',
                level='debug',
            )
        return None


def _maybe_persist_token_for_subprocesses(path: str, token: str, token_name: str) -> None:
    if not is_env_truthy(os.environ.get('vivian_CODE_REMOTE')):
        return
    try:
        os.makedirs(CCR_TOKEN_DIR, mode=0o700, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(token)
        os.chmod(path, 0o600)
        logForDebugging(f'Persisted {token_name} to {path} for subprocess access')
    except Exception as error:
        logForDebugging(
            f'Failed to persist {token_name} to disk (non-fatal): {error_message(error)}',
            level='error',
        )


def getTokenFromFileDescriptor():
    """Read token via file descriptor, falling back to well-known file.
Uses global state to cache the result since file descriptors can only be read once."""
    global _token_read_attempted
    if _token_read_attempted:
        return getSessionIngressToken()

    fd_env = os.environ.get('vivian_CODE_WEBSOCKET_AUTH_FILE_DESCRIPTOR')
    if not fd_env:
        path = os.environ.get('vivian_SESSION_INGRESS_TOKEN_FILE') or CCR_SESSION_INGRESS_TOKEN_PATH
        from_file = _read_token_from_well_known_file(path, 'session ingress token')
        setSessionIngressToken(from_file)
        _token_read_attempted = True
        return from_file

    try:
        fd = int(fd_env)
    except ValueError:
        logForDebugging(
            f'vivian_CODE_WEBSOCKET_AUTH_FILE_DESCRIPTOR must be a valid file descriptor number, got: {fd_env}',
            level='error',
        )
        setSessionIngressToken(None)
        _token_read_attempted = True
        return None

    try:
        fd_path = f'/dev/fd/{fd}' if os.sys.platform in ('darwin', 'freebsd') else f'/proc/self/fd/{fd}'
        token = open(fd_path, 'r', encoding='utf-8').read().strip()
        if not token:
            logForDebugging('File descriptor contained empty token', level='error')
            setSessionIngressToken(None)
            _token_read_attempted = True
            return None
        logForDebugging(f'Successfully read token from file descriptor {fd}')
        setSessionIngressToken(token)
        _maybe_persist_token_for_subprocesses(
            CCR_SESSION_INGRESS_TOKEN_PATH,
            token,
            'session ingress token',
        )
        _token_read_attempted = True
        return token
    except Exception as error:
        logForDebugging(
            f'Failed to read token from file descriptor {fd}: {error_message(error)}',
            level='error',
        )
        path = os.environ.get('vivian_SESSION_INGRESS_TOKEN_FILE') or CCR_SESSION_INGRESS_TOKEN_PATH
        from_file = _read_token_from_well_known_file(path, 'session ingress token')
        setSessionIngressToken(from_file)
        _token_read_attempted = True
        return from_file


def getSessionIngressAuthToken():
    """Get session ingress authentication token.

Priority order:
1. Environment variable (vivian_CODE_SESSION_ACCESS_TOKEN) — set at spawn time,
updated in-process via updateSessionIngressAuthToken or
update_environment_variables stdin message from the parent bridge process.
2. File descriptor (legacy path) — vivian_CODE_WEBSOCKET_AUTH_FILE_DESCRIPTOR,
read once and cached.
3. Well-known file — vivian_SESSION_INGRESS_TOKEN_FILE env var path, or
/home/vivian/.vivian/remote/.session_ingress_token. Covers subprocesses
that can't inherit the FD."""
    env_token = os.environ.get('vivian_CODE_SESSION_ACCESS_TOKEN')
    if env_token:
        return env_token
    return getTokenFromFileDescriptor()


def getSessionIngressAuthHeaders():
    """Build auth headers for the current session token.
Session keys (sk-ant-sid) use Cookie auth + X-Organization-Uuid;
JWTs use Bearer auth."""
    token = getSessionIngressAuthToken()
    if not token:
        return {}
    if token.startswith('sk-ant-sid'):
        headers = {'Cookie': f'sessionKey={token}'}
        org_uuid = os.environ.get('vivian_CODE_ORGANIZATION_UUID')
        if org_uuid:
            headers['X-Organization-Uuid'] = org_uuid
        return headers
    return {'Authorization': f'Bearer {token}'}


def updateSessionIngressAuthToken(token):
    """Update the session ingress auth token in-process by setting the env var.
Used by the REPL bridge to inject a fresh token after reconnection
without restarting the process."""
    os.environ['vivian_CODE_SESSION_ACCESS_TOKEN'] = token


get_token_from_file_descriptor = getTokenFromFileDescriptor
get_session_ingress_auth_token = getSessionIngressAuthToken
get_session_ingress_auth_headers = getSessionIngressAuthHeaders
update_session_ingress_auth_token = updateSessionIngressAuthToken


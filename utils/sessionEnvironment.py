"""
passpasspasspasspass of src/utils/sessionEnvironment
"""
from __future__ import annotations

import os
import re
import asyncio
from pathlib import Path

from ..bootstrap.state import getSessionId
from .debug import logForDebugging
from .envUtils import get_vivian_config_home_dir
from .errors import error_message, get_errno_code
from .platform import get_platform


_HOOK_ENV_PRIORITY = {
    'setup': 0,
    'sessionstart': 1,
    'cwdchanged': 2,
    'filechanged': 3,
}
HOOK_ENV_REGEX = re.compile(r'^(setup|sessionstart|cwdchanged|filechanged)-hook-(\d+)\.sh$')
_SESSION_ENV_UNSET = object()
_session_env_script: str | None | object = _SESSION_ENV_UNSET


async def getSessionEnvDirPath():
    session_env_dir = Path(get_vivian_config_home_dir()) / 'session-env' / getSessionId()
    await asyncio.to_thread(session_env_dir.mkdir, parents=True, exist_ok=True)
    return str(session_env_dir)


async def getHookEnvFilePath(hookEvent, hookIndex):
    prefix = str(hookEvent).lower()
    return str(Path(await getSessionEnvDirPath()) / f'{prefix}-hook-{hookIndex}.sh')


async def clearCwdEnvFiles():
    try:
        directory = await getSessionEnvDirPath()
        files = await asyncio.to_thread(os.listdir, directory)
        for filename in files:
            if (
                (filename.startswith('filechanged-hook-') or filename.startswith('cwdchanged-hook-'))
                and HOOK_ENV_REGEX.match(filename)
            ):
                await asyncio.to_thread(Path(directory, filename).write_text, '', encoding='utf-8')
    except Exception as error:
        if get_errno_code(error) != 'ENOENT':
            logForDebugging(f'Failed to clear cwd env files: {error_message(error)}')


def invalidateSessionEnvCache():
    logForDebugging('Invalidating session environment cache')
    global _session_env_script
    _session_env_script = _SESSION_ENV_UNSET


async def getSessionEnvironmentScript():
    global _session_env_script
    if get_platform() == 'windows':
        logForDebugging('Session environment not yet supported on Windows')
        return None

    if _session_env_script is not _SESSION_ENV_UNSET:
        return _session_env_script

    scripts: list[str] = []
    env_file = os.environ.get('vivian_ENV_FILE')
    if env_file:
        try:
            env_script = (await asyncio.to_thread(Path(env_file).read_text, encoding='utf-8')).strip()
            if env_script:
                scripts.append(env_script)
                logForDebugging(
                    f'Session environment loaded from vivian_ENV_FILE: {env_file} ({len(env_script)} chars)'
                )
        except Exception as error:
            if get_errno_code(error) != 'ENOENT':
                logForDebugging(f'Failed to read vivian_ENV_FILE: {error_message(error)}')

    session_env_dir = await getSessionEnvDirPath()
    try:
        files = await asyncio.to_thread(os.listdir, session_env_dir)
        hook_files = sorted(
            [filename for filename in files if HOOK_ENV_REGEX.match(filename)],
            key=lambda filename: (
                _HOOK_ENV_PRIORITY.get(HOOK_ENV_REGEX.match(filename).group(1), 99),
                int(HOOK_ENV_REGEX.match(filename).group(2)),
            ),
        )
        for filename in hook_files:
            file_path = str(Path(session_env_dir) / filename)
            try:
                content = (await asyncio.to_thread(Path(file_path).read_text, encoding='utf-8')).strip()
                if content:
                    scripts.append(content)
            except Exception as error:
                if get_errno_code(error) != 'ENOENT':
                    logForDebugging(f'Failed to read hook file {file_path}: {error_message(error)}')
        if hook_files:
            logForDebugging(f'Session environment loaded from {len(hook_files)} hook file(s)')
    except Exception as error:
        if get_errno_code(error) != 'ENOENT':
            logForDebugging(f'Failed to load session environment from hooks: {error_message(error)}')

    if not scripts:
        logForDebugging('No session environment scripts found')
        _session_env_script = None
        return None

    _session_env_script = '\n'.join(scripts)
    logForDebugging(f'Session environment script ready ({len(_session_env_script)} chars total)')
    return _session_env_script


def sortHookEnvFiles(a, b):
    a_match = HOOK_ENV_REGEX.match(a or '')
    b_match = HOOK_ENV_REGEX.match(b or '')
    a_type = a_match.group(1) if a_match else ''
    b_type = b_match.group(1) if b_match else ''
    if a_type != b_type:
        return _HOOK_ENV_PRIORITY.get(a_type, 99) - _HOOK_ENV_PRIORITY.get(b_type, 99)
    a_index = int(a_match.group(2)) if a_match else 0
    b_index = int(b_match.group(2)) if b_match else 0
    return a_index - b_index


get_session_env_dir_path = getSessionEnvDirPath
get_hook_env_file_path = getHookEnvFilePath
clear_cwd_env_files = clearCwdEnvFiles
invalidate_session_env_cache = invalidateSessionEnvCache
get_session_environment_script = getSessionEnvironmentScript
sort_hook_env_files = sortHookEnvFiles


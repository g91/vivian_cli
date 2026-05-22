"""Teleport package exports and resume helpers."""
from __future__ import annotations

from typing import Any

from ...bootstrap.state import getOriginalCwd
from ..conversationRecovery import deserializeMessages
from ..errors import TeleportOperationError
from ..git import findGitRoot, get_branch, getIsClean
from ..log import logError
from ..messages import createUserMessage
from ...services.analytics.index import logEvent


def createTeleportResumeSystemMessage(branchError):
	if branchError is None:
		content = 'Session resumed'
		subtype = 'suggestion'
	else:
		formatted = (
			branchError.formatted_message
			if isinstance(branchError, TeleportOperationError)
			else str(branchError)
		)
		content = f'Session resumed without branch: {formatted}'
		subtype = 'warning'
	return {
		'role': 'system',
		'type': 'system',
		'subtype': subtype,
		'message': {'role': 'system', 'content': content},
		'content': content,
	}


def createTeleportResumeUserMessage():
	message = createUserMessage(
		{
			'content': (
				'This session is being continued from another machine. '
				f'Application state may have changed. The updated working directory is {getOriginalCwd()}'
			)
		}
	)
	message['isMeta'] = True
	return message


async def getCurrentBranch():
	return (await get_branch() or '').strip()


async def validateGitState():
	is_clean = await getIsClean(ignoreUntracked=True)
	if is_clean:
		return True
	logEvent('tengu_teleport_error_git_not_clean', {})
	raise TeleportOperationError(
		'Git working directory is not clean. Please commit or stash your changes before using --teleport.',
		'Error: Git working directory is not clean. Please commit or stash your changes before using --teleport.\n',
	)


async def fetchFromOrigin(branch=None):
	import asyncio as _asyncio

	args = ['git', 'fetch', 'origin']
	if branch:
		args = ['git', 'fetch', 'origin', f'{branch}:{branch}']
	process = await _asyncio.create_subprocess_exec(
		*args,
		stdout=_asyncio.subprocess.PIPE,
		stderr=_asyncio.subprocess.PIPE,
	)
	_stdout, stderr = await process.communicate()
	if process.returncode == 0:
		return True
	if branch and b'refspec' in (stderr or b''):
		fallback = await _asyncio.create_subprocess_exec(
			'git', 'fetch', 'origin', branch,
			stdout=_asyncio.subprocess.PIPE,
			stderr=_asyncio.subprocess.PIPE,
		)
		await fallback.communicate()
		return fallback.returncode == 0
	return False


async def ensureUpstreamIsSet(branchName):
	import asyncio as _asyncio

	check = await _asyncio.create_subprocess_exec(
		'git', 'rev-parse', '--abbrev-ref', f'{branchName}@{{upstream}}',
		stdout=_asyncio.subprocess.PIPE,
		stderr=_asyncio.subprocess.PIPE,
	)
	await check.communicate()
	if check.returncode == 0:
		return True

	remote_check = await _asyncio.create_subprocess_exec(
		'git', 'rev-parse', '--verify', f'origin/{branchName}',
		stdout=_asyncio.subprocess.PIPE,
		stderr=_asyncio.subprocess.PIPE,
	)
	await remote_check.communicate()
	if remote_check.returncode != 0:
		return False

	set_upstream = await _asyncio.create_subprocess_exec(
		'git', 'branch', '--set-upstream-to', f'origin/{branchName}', branchName,
		stdout=_asyncio.subprocess.PIPE,
		stderr=_asyncio.subprocess.PIPE,
	)
	await set_upstream.communicate()
	return set_upstream.returncode == 0


async def checkoutBranch(branchName):
	import asyncio as _asyncio

	if branchName is None:
		return False
	checkout = await _asyncio.create_subprocess_exec(
		'git', 'checkout', branchName,
		stdout=_asyncio.subprocess.PIPE,
		stderr=_asyncio.subprocess.PIPE,
	)
	_stdout, stderr = await checkout.communicate()
	if checkout.returncode != 0:
		tracked = await _asyncio.create_subprocess_exec(
			'git', 'checkout', '-b', branchName, '--track', f'origin/{branchName}',
			stdout=_asyncio.subprocess.PIPE,
			stderr=_asyncio.subprocess.PIPE,
		)
		_stdout, stderr = await tracked.communicate()
		if tracked.returncode != 0:
			fallback = await _asyncio.create_subprocess_exec(
				'git', 'checkout', '--track', f'origin/{branchName}',
				stdout=_asyncio.subprocess.PIPE,
				stderr=_asyncio.subprocess.PIPE,
			)
			_stdout, stderr = await fallback.communicate()
			if fallback.returncode != 0:
				logEvent('tengu_teleport_error_branch_checkout_failed', {})
				raise TeleportOperationError(
					f"Failed to checkout branch '{branchName}': {(stderr or b'').decode('utf-8', 'replace').strip()}",
					f"Failed to checkout branch '{branchName}'\n",
				)
	await ensureUpstreamIsSet(branchName)
	return True


def processMessagesForTeleportResume(messages, error):
	try:
		deserialized = deserializeMessages(messages)
		base_messages = deserialized if isinstance(deserialized, list) else (messages if isinstance(messages, list) else [])
	except Exception:
		base_messages = messages if isinstance(messages, list) else []
	return [*base_messages, createTeleportResumeUserMessage(), createTeleportResumeSystemMessage(error)]


async def checkOutTeleportedSessionBranch(branch=None):
	current_branch = await getCurrentBranch()
	if not branch:
		return {'branchName': current_branch, 'branchError': None}

	branch_error = None
	try:
		git_root = findGitRoot(getOriginalCwd())
		if git_root:
			await fetchFromOrigin(branch)
		await checkoutBranch(branch)
		current_branch = await getCurrentBranch()
	except Exception as exc:
		branch_error = exc
		logError(exc)

	return {'branchName': current_branch, 'branchError': branch_error}


async def validateSessionRepository(sessionData):
	return bool(sessionData)


async def teleportResumeCodeSession(sessionId, onProgress=None):
	def _progress(step: str) -> None:
		if callable(onProgress):
			onProgress(step)

	from .api import fetchSession, getBranchFromSession

	_progress('validating')
	session_data = await fetchSession(sessionId)
	await validateSessionRepository(session_data)
	branch = getBranchFromSession(session_data)
	if branch:
		_progress('fetching_branch')
	checkout_result = await checkOutTeleportedSessionBranch(branch)
	_progress('done')
	return {
		'sessionId': sessionId,
		'sessionData': session_data,
		'branchName': checkout_result.get('branchName'),
		'branchError': checkout_result.get('branchError'),
		'messages': processMessagesForTeleportResume([], checkout_result.get('branchError')),
	}


create_teleport_resume_system_message = createTeleportResumeSystemMessage
create_teleport_resume_user_message = createTeleportResumeUserMessage
get_current_branch_name = getCurrentBranch
process_messages_for_teleport_resume = processMessagesForTeleportResume
check_out_teleported_session_branch = checkOutTeleportedSessionBranch
teleport_resume_code_session = teleportResumeCodeSession

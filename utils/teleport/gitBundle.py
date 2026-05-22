"""Git bundle creation and upload helpers for teleport session seeding."""
from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from ...constants.system import getCwd
from ...services.analytics.growthbook import getFeatureValue_CACHED_MAY_BE_STALE
from ...services.analytics.index import logEvent
from ..debug import logForDebugging
from ..errors import error_message
from ..execFileNoThrow import exec_file_no_throw
from ..git import findGitRoot
from ..tempfile import generate_temp_file_path


FILES_API_BETA_HEADER = 'files-api-2025-04-14,oauth-2025-04-20'
ANTHROPIC_VERSION = '2023-06-01'
DEFAULT_BUNDLE_MAX_BYTES = 100 * 1024 * 1024
MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024

BundleScope = str
BundleUploadResult = dict[str, Any]
BundleFailReason = str
BundleCreateResult = dict[str, Any]


def _get_default_api_base_url() -> str:
    return (
        os.environ.get('ANTHROPIC_BASE_URL')
        or os.environ.get('vivian_CODE_API_BASE_URL')
        or 'https://api.anthropic.com'
    )


async def _git(args: list[str], *, cwd: str, timeout: float | None = 600) -> dict[str, Any]:
    return await exec_file_no_throw('git', args, cwd=cwd, timeout=timeout)


async def _delete_seed_refs(git_root: str) -> None:
    for ref in ['refs/seed/stash', 'refs/seed/root']:
        await _git(['update-ref', '-d', ref], cwd=git_root)


def _build_upload_body(content: bytes, relative_path: str) -> tuple[bytes, str]:
    boundary = f'----FormBoundary{uuid.uuid4()}'
    filename = os.path.basename(relative_path)
    body = b''.join(
        [
            (
                f'--{boundary}\r\n'
                f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                f'Content-Type: application/octet-stream\r\n\r\n'
            ).encode('utf-8'),
            content,
            b'\r\n',
            (
                f'--{boundary}\r\n'
                f'Content-Disposition: form-data; name="purpose"\r\n\r\n'
                f'user_data\r\n'
            ).encode('utf-8'),
            f'--{boundary}--\r\n'.encode('utf-8'),
        ]
    )
    return body, boundary


def _upload_bundle_file_sync(
    file_path: str,
    relative_path: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    try:
        content = Path(file_path).read_bytes()
    except Exception as exc:
        return {'path': relative_path, 'error': error_message(exc), 'success': False}

    file_size = len(content)
    if file_size > MAX_FILE_SIZE_BYTES:
        return {
            'path': relative_path,
            'error': f'File exceeds maximum size of {MAX_FILE_SIZE_BYTES} bytes (actual: {file_size})',
            'success': False,
        }

    body, boundary = _build_upload_body(content, relative_path)
    base_url = config.get('baseUrl') or _get_default_api_base_url()
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/files",
        data=body,
        headers={
            'Authorization': f"Bearer {config['oauthToken']}",
            'anthropic-version': ANTHROPIC_VERSION,
            'anthropic-beta': FILES_API_BETA_HEADER,
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'Content-Length': str(len(body)),
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode('utf-8', 'replace').strip() or str(exc)
        if exc.code == 401:
            message = 'Authentication failed: invalid or missing API key'
        elif exc.code == 403:
            message = 'Access denied for upload'
        elif exc.code == 413:
            message = 'File too large for upload'
        return {'path': relative_path, 'error': message, 'success': False}
    except Exception as exc:
        return {'path': relative_path, 'error': error_message(exc), 'success': False}

    file_id = payload.get('id') if isinstance(payload, dict) else None
    if not file_id:
        return {'path': relative_path, 'error': 'Upload succeeded but no file ID returned', 'success': False}

    logForDebugging(f'[gitBundle] Uploaded {file_size} bytes as file_id {file_id}')
    return {
        'path': relative_path,
        'fileId': file_id,
        'size': file_size,
        'success': True,
    }


async def _upload_bundle_file(
    file_path: str,
    relative_path: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    return await asyncio.to_thread(_upload_bundle_file_sync, file_path, relative_path, config)


async def _bundleWithFallback(
    gitRoot: str,
    bundlePath: str,
    maxBytes: int,
    hasStash: bool,
    signal: Any,
) -> BundleCreateResult:
    del signal
    extra = ['refs/seed/stash'] if hasStash else []

    async def mk_bundle(base: str) -> dict[str, Any]:
        return await _git(['bundle', 'create', bundlePath, base, *extra], cwd=gitRoot)

    all_result = await mk_bundle('--all')
    if all_result.get('code') != 0:
        return {
            'ok': False,
            'error': f"git bundle create --all failed ({all_result.get('code')}): {all_result.get('stderr', '')[:200]}",
            'failReason': 'git_error',
        }

    all_size = os.path.getsize(bundlePath)
    if all_size <= maxBytes:
        return {'ok': True, 'size': all_size, 'scope': 'all'}

    logForDebugging(
        f"[gitBundle] --all bundle is {(all_size / 1024 / 1024):.1f}MB (> {(maxBytes / 1024 / 1024):.0f}MB), retrying HEAD-only"
    )
    head_result = await mk_bundle('HEAD')
    if head_result.get('code') != 0:
        return {
            'ok': False,
            'error': f"git bundle create HEAD failed ({head_result.get('code')}): {head_result.get('stderr', '')[:200]}",
            'failReason': 'git_error',
        }

    head_size = os.path.getsize(bundlePath)
    if head_size <= maxBytes:
        return {'ok': True, 'size': head_size, 'scope': 'head'}

    logForDebugging(
        f"[gitBundle] HEAD bundle is {(head_size / 1024 / 1024):.1f}MB, retrying squashed-root"
    )
    tree_ref = 'refs/seed/stash^{tree}' if hasStash else 'HEAD^{tree}'
    commit_tree = await _git(['commit-tree', tree_ref, '-m', 'seed'], cwd=gitRoot)
    if commit_tree.get('code') != 0:
        return {
            'ok': False,
            'error': f"git commit-tree failed ({commit_tree.get('code')}): {commit_tree.get('stderr', '')[:200]}",
            'failReason': 'git_error',
        }

    squashed_sha = commit_tree.get('stdout', '').strip()
    await _git(['update-ref', 'refs/seed/root', squashed_sha], cwd=gitRoot)
    squash_result = await _git(['bundle', 'create', bundlePath, 'refs/seed/root'], cwd=gitRoot)
    if squash_result.get('code') != 0:
        return {
            'ok': False,
            'error': (
                f"git bundle create refs/seed/root failed ({squash_result.get('code')}): "
                f"{squash_result.get('stderr', '')[:200]}"
            ),
            'failReason': 'git_error',
        }

    squash_size = os.path.getsize(bundlePath)
    if squash_size <= maxBytes:
        return {'ok': True, 'size': squash_size, 'scope': 'squashed'}

    return {
        'ok': False,
        'error': 'Repo is too large to bundle. Please setup GitHub on https://api-vivian.d0a.net/code',
        'failReason': 'too_large',
    }


async def createAndUploadGitBundle(config: dict[str, Any], opts: dict[str, Any] | None = None) -> BundleUploadResult:
    opts = opts or {}
    workdir = opts.get('cwd') or getCwd()
    git_root = findGitRoot(workdir)
    if not git_root:
        return {'success': False, 'error': 'Not in a git repository'}

    await _delete_seed_refs(git_root)

    ref_check = await _git(['for-each-ref', '--count=1', 'refs/'], cwd=git_root)
    if ref_check.get('code') == 0 and ref_check.get('stdout', '').strip() == '':
        logEvent('tengu_ccr_bundle_upload', {'outcome': 'empty_repo'})
        return {
            'success': False,
            'error': 'Repository has no commits yet',
            'failReason': 'empty_repo',
        }

    stash_result = await _git(['stash', 'create'], cwd=git_root)
    wip_stash_sha = stash_result.get('stdout', '').strip() if stash_result.get('code') == 0 else ''
    has_wip = wip_stash_sha != ''
    if stash_result.get('code') != 0:
        logForDebugging(
            f"[gitBundle] git stash create failed ({stash_result.get('code')}), proceeding without WIP: {stash_result.get('stderr', '')[:200]}"
        )
    elif has_wip:
        logForDebugging(f'[gitBundle] Captured WIP as stash {wip_stash_sha}')
        await _git(['update-ref', 'refs/seed/stash', wip_stash_sha], cwd=git_root)

    bundle_path = generate_temp_file_path('ccr-seed', '.bundle')

    try:
        max_bytes = (
            getFeatureValue_CACHED_MAY_BE_STALE('tengu_ccr_bundle_max_bytes', None)
            or DEFAULT_BUNDLE_MAX_BYTES
        )
        bundle = await _bundleWithFallback(
            git_root,
            bundle_path,
            int(max_bytes),
            has_wip,
            opts.get('signal'),
        )
        if not bundle.get('ok'):
            logForDebugging(f"[gitBundle] {bundle.get('error')}")
            logEvent(
                'tengu_ccr_bundle_upload',
                {'outcome': bundle.get('failReason'), 'max_bytes': int(max_bytes)},
            )
            return {
                'success': False,
                'error': bundle.get('error', 'Unknown bundle error'),
                'failReason': bundle.get('failReason'),
            }

        upload = await _upload_bundle_file(bundle_path, '_source_seed.bundle', config)
        if not upload.get('success'):
            logEvent('tengu_ccr_bundle_upload', {'outcome': 'failed'})
            return {'success': False, 'error': upload.get('error', 'Upload failed')}

        logEvent(
            'tengu_ccr_bundle_upload',
            {
                'outcome': 'success',
                'size_bytes': upload.get('size'),
                'scope': bundle.get('scope'),
                'has_wip': has_wip,
            },
        )
        return {
            'success': True,
            'fileId': upload.get('fileId'),
            'bundleSizeBytes': upload.get('size'),
            'scope': bundle.get('scope'),
            'hasWip': has_wip,
        }
    finally:
        try:
            os.unlink(bundle_path)
        except Exception:
            logForDebugging(f'[gitBundle] Could not delete {bundle_path} (non-fatal)')
        await _delete_seed_refs(git_root)


create_and_upload_git_bundle = createAndUploadGitBundle
bundle_with_fallback = _bundleWithFallback


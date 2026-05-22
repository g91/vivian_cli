"""Port of src/utils/filePersistence/filePersistence.ts"""
from __future__ import annotations
import asyncio
import os
import os.path
import time
from typing import Any, Callable, Dict, List, Optional

from vivian_cli.utils.cwd import getCwd
from vivian_cli.utils.errors import errorMessage
from vivian_cli.utils.log import logError
from vivian_cli.utils.filePersistence.outputsScanner import (
    findModifiedFiles,
    getEnvironmentKind,
    logDebug,
)

# Constants (from types.ts)
OUTPUTS_SUBDIR = "outputs"
FILE_COUNT_LIMIT = 1000
DEFAULT_UPLOAD_CONCURRENCY = 10

FilesPersistedEventData = Dict[str, Any]
PersistedFile = Dict[str, str]
FailedPersistence = Dict[str, str]
FilesApiConfig = Dict[str, str]
TurnStartTime = float


async def runFilePersistence(
    turnStartTime: TurnStartTime,
    signal: Optional[Any] = None,
) -> Optional[FilesPersistedEventData]:
    """Execute file persistence for modified files in the outputs directory.

    Assembles all config internally:
    - Checks environment kind (vivian_CODE_ENVIRONMENT_KIND)
    - Retrieves session access token
    - Requires vivian_CODE_REMOTE_SESSION_ID for session ID

    Returns event data, or None if not enabled or no files to persist.
    """
    environment_kind = getEnvironmentKind()
    if environment_kind != "byoc":
        return None

    try:
        from vivian_cli.utils.sessionIngressAuth import getSessionIngressAuthToken
        session_access_token = getSessionIngressAuthToken()
    except Exception:
        session_access_token = None

    if not session_access_token:
        return None

    session_id = os.environ.get("vivian_CODE_REMOTE_SESSION_ID")
    if not session_id:
        logError(
            Exception(
                "File persistence enabled but vivian_CODE_REMOTE_SESSION_ID is not set"
            )
        )
        return None

    config: FilesApiConfig = {
        "oauthToken": session_access_token,
        "sessionId": session_id,
    }

    outputs_dir = os.path.join(getCwd(), session_id, OUTPUTS_SUBDIR)

    # Check if aborted
    if signal is not None and getattr(signal, "aborted", False):
        logDebug("Persistence aborted before processing")
        return None

    start_time = time.time() * 1000  # ms

    try:
        from vivian_cli.utils.services.analytics import logEvent
        logEvent("tengu_file_persistence_started", {"mode": environment_kind})
    except Exception:
        pass

    try:
        result: FilesPersistedEventData
        if environment_kind == "byoc":
            result = await executeBYOCPersistence(
                turnStartTime, config, outputs_dir, signal
            )
        else:
            result = executeCloudPersistence()

        if len(result.get("files", [])) == 0 and len(result.get("failed", [])) == 0:
            return None

        duration_ms = time.time() * 1000 - start_time
        try:
            from vivian_cli.utils.services.analytics import logEvent
            logEvent(
                "tengu_file_persistence_completed",
                {
                    "success_count": len(result.get("files", [])),
                    "failure_count": len(result.get("failed", [])),
                    "duration_ms": duration_ms,
                    "mode": environment_kind,
                },
            )
        except Exception:
            pass

        return result

    except Exception as error:
        logError(error)
        logDebug(f"File persistence failed: {error}")

        duration_ms = time.time() * 1000 - start_time
        try:
            from vivian_cli.utils.services.analytics import logEvent
            logEvent(
                "tengu_file_persistence_completed",
                {
                    "success_count": 0,
                    "failure_count": 0,
                    "duration_ms": duration_ms,
                    "mode": environment_kind,
                    "error": "exception",
                },
            )
        except Exception:
            pass

        return {
            "files": [],
            "failed": [
                {
                    "filename": outputs_dir,
                    "error": errorMessage(error),
                }
            ],
        }


async def executeBYOCPersistence(
    turnStartTime: TurnStartTime,
    config: FilesApiConfig,
    outputsDir: str,
    signal: Optional[Any] = None,
) -> FilesPersistedEventData:
    """Execute BYOC mode persistence: scan local filesystem for modified files,
    then upload to Files API.
    """
    modified_files = await findModifiedFiles(turnStartTime, outputsDir)

    if not modified_files:
        logDebug("No modified files to persist")
        return {"files": [], "failed": []}

    logDebug(f"Found {len(modified_files)} modified files")

    if signal is not None and getattr(signal, "aborted", False):
        return {"files": [], "failed": []}

    if len(modified_files) > FILE_COUNT_LIMIT:
        logDebug(
            f"File count limit exceeded: {len(modified_files)} > {FILE_COUNT_LIMIT}"
        )
        try:
            from vivian_cli.utils.services.analytics import logEvent
            logEvent(
                "tengu_file_persistence_limit_exceeded",
                {"file_count": len(modified_files), "limit": FILE_COUNT_LIMIT},
            )
        except Exception:
            pass
        return {
            "files": [],
            "failed": [
                {
                    "filename": outputsDir,
                    "error": (
                        f"Too many files modified ({len(modified_files)}). "
                        f"Maximum: {FILE_COUNT_LIMIT}."
                    ),
                }
            ],
        }

    files_to_process = []
    for file_path in modified_files:
        relative_path = os.path.relpath(file_path, outputsDir)
        if relative_path.startswith(".."):
            logDebug(f"Skipping file outside outputs directory: {relative_path}")
            continue
        files_to_process.append({"path": file_path, "relativePath": relative_path})

    logDebug(f"BYOC mode: uploading {len(files_to_process)} files")

    try:
        from vivian_cli.utils.services.api.filesApi import uploadSessionFiles
        results = await uploadSessionFiles(
            files_to_process, config, DEFAULT_UPLOAD_CONCURRENCY
        )
    except Exception as upload_error:
        logDebug(f"Upload failed: {upload_error}")
        return {
            "files": [],
            "failed": [
                {"filename": f["path"], "error": str(upload_error)}
                for f in files_to_process
            ],
        }

    persisted_files: List[PersistedFile] = []
    failed_files: List[FailedPersistence] = []

    for result in results:
        if result.get("success"):
            persisted_files.append(
                {"filename": result["path"], "file_id": result["fileId"]}
            )
        else:
            failed_files.append(
                {"filename": result["path"], "error": result.get("error", "")}
            )

    logDebug(
        f"BYOC persistence complete: {len(persisted_files)} uploaded, "
        f"{len(failed_files)} failed"
    )

    return {"files": persisted_files, "failed": failed_files}


def executeCloudPersistence() -> FilesPersistedEventData:
    """Execute Cloud (1P) mode persistence.
    TODO: Read file_id from xattr on output files.
    """
    logDebug("Cloud mode: xattr-based file ID reading not yet implemented")
    return {"files": [], "failed": []}


async def executeFilePersistence(
    turnStartTime: TurnStartTime,
    signal: Any,
    onResult: Optional[Callable[[FilesPersistedEventData], None]] = None,
) -> None:
    """Execute file persistence and emit result via callback. Handles errors internally."""
    try:
        result = await runFilePersistence(turnStartTime, signal)
        if result is not None and onResult is not None:
            onResult(result)
    except Exception as error:
        logError(error)


def isFilePersistenceEnabled() -> bool:
    """Check if file persistence is enabled.
    Requires: environment kind byoc, session access token, and vivian_CODE_REMOTE_SESSION_ID.
    """
    try:
        from vivian_cli.utils.sessionIngressAuth import getSessionIngressAuthToken
        has_token = bool(getSessionIngressAuthToken())
    except Exception:
        has_token = False

    return (
        getEnvironmentKind() == "byoc"
        and has_token
        and bool(os.environ.get("vivian_CODE_REMOTE_SESSION_ID"))
    )

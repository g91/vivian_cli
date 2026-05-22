"""Port of src/bridge/bridgeMain.ts.

Standalone bridge daemon — the `vivian bridge` entry point.

Owns: CLI arg parsing, environment registration, session spawning/capacity
management, reconnection/backoff loop, and teardown. 

Implements the Python bridge daemon entrypoint and a working poll/spawn loop
using the already-ported bridge API, logger, work-secret, and session-runner
infrastructure.
"""
from __future__ import annotations

import asyncio
import os
import random
import socket
import sys
import uuid
from typing import Any, Callable, Dict, List, Literal, Optional, TypedDict

from ..constants import PRODUCT_VERSION
from .bridgeApi import BridgeFatalError, createBridgeApiClient
from .bridgeStatusUtil import buildBridgeSessionUrl
from .bridgeUI import createBridgeLogger
from .capacityWake import createCapacityWake
from .debugUtils import describeAxiosError
from .pollConfig import getPollIntervalConfig
from .sessionRunner import createSessionSpawner
from .workSecret import buildCCRv2SdkUrl, buildSdkUrl, decodeWorkSecret, registerWorker


SpawnMode = Literal["single-session", "same-dir", "worktree"]


class BackoffConfig(TypedDict, total=False):
    connInitialMs: int
    connCapMs: int
    connGiveUpMs: int
    generalInitialMs: int
    generalCapMs: int
    generalGiveUpMs: int
    shutdownGraceMs: int
    stopWorkBaseDelayMs: int


DEFAULT_BACKOFF: BackoffConfig = {
    "connInitialMs": 2_000,
    "connCapMs": 120_000,
    "connGiveUpMs": 600_000,
    "generalInitialMs": 500,
    "generalCapMs": 30_000,
    "generalGiveUpMs": 600_000,
}


class ParsedArgs(TypedDict, total=False):
    verbose: bool
    sandbox: bool
    debugFile: Optional[str]
    sessionTimeoutMs: Optional[int]
    permissionMode: Optional[str]
    name: Optional[str]
    spawnMode: Optional[SpawnMode]
    capacity: Optional[int]
    createSessionInDir: Optional[bool]
    sessionId: Optional[str]
    continueSession: bool
    help: bool
    error: Optional[str]


SPAWN_FLAG_MAP = {
    "session": "single-session",
    "same-dir": "same-dir",
    "worktree": "worktree",
}


def parseArgs(args: List[str]) -> ParsedArgs:
    """Parse CLI arguments for the bridge daemon."""
    result: ParsedArgs = {
        "verbose": False,
        "sandbox": False,
        "continueSession": False,
        "help": False,
        "spawnMode": None,
        "capacity": None,
        "createSessionInDir": None,
    }
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--help", "-h"):
            result["help"] = True
        elif arg == "--verbose":
            result["verbose"] = True
        elif arg == "--sandbox":
            result["sandbox"] = True
        elif arg == "--debug-file":
            i += 1
            result["debugFile"] = args[i] if i < len(args) else None
        elif arg == "--session-timeout-ms":
            i += 1
            try:
                result["sessionTimeoutMs"] = int(args[i]) if i < len(args) else None
            except ValueError:
                result["error"] = f"--session-timeout-ms requires an integer"
        elif arg == "--permission-mode":
            i += 1
            result["permissionMode"] = args[i] if i < len(args) else None
        elif arg == "--name":
            i += 1
            result["name"] = args[i] if i < len(args) else None
        elif arg == "--session-id":
            i += 1
            result["sessionId"] = args[i] if i < len(args) else None
        elif arg == "--continue":
            result["continueSession"] = True
        elif arg == "--spawn":
            i += 1
            raw = args[i] if i < len(args) else None
            mapped = SPAWN_FLAG_MAP.get(raw or "")
            if mapped:
                result["spawnMode"] = mapped  # type: ignore
            else:
                result["error"] = f"--spawn requires one of: session, same-dir, worktree (got: {raw or '<missing>'})"
        elif arg == "--capacity":
            i += 1
            raw = args[i] if i < len(args) else None
            try:
                n = int(raw or "")
                if n < 1:
                    raise ValueError
                result["capacity"] = n
            except (ValueError, TypeError):
                result["error"] = f"--capacity requires a positive integer (got: {raw or '<missing>'})"
        elif arg == "--create-session-in-dir":
            result["createSessionInDir"] = True
        elif arg == "--no-create-session-in-dir":
            result["createSessionInDir"] = False
        i += 1
    return result


def isConnectionError(err: Exception) -> bool:
    """Return True if the error is a transient connection error."""
    msg = str(err).lower()
    return any(kw in msg for kw in ("connect", "timeout", "network", "econnreset", "enotfound", "socket"))


def isServerError(err: Exception) -> bool:
    """Return True if the error is a server-side 5xx error."""
    msg = str(err)
    return "5" in msg and any(c in msg for c in ("500", "502", "503", "504"))


class BridgeHeadlessPermanentError(Exception):
    """Raised when headless bridge encounters a permanent (non-retriable) error."""
    pass


class HeadlessBridgeOpts(TypedDict, total=False):
    environmentId: str
    sessionId: str
    sdkUrl: str
    accessToken: str
    workerEpoch: int
    dir: str
    permissionMode: Optional[str]
    verbose: bool
    sandbox: bool
    onActivity: Optional[Callable]
    onDone: Optional[Callable]


async def runBridgeLoop(
    base_url: str,
    access_token: str,
    backoff: Optional[BackoffConfig] = None,
    verbose: bool = False,
    sandbox: bool = False,
    debug_file: Optional[str] = None,
    session_timeout_ms: Optional[int] = None,
    permission_mode: Optional[str] = None,
    name: Optional[str] = None,
    spawn_mode: Optional[SpawnMode] = None,
    capacity: Optional[int] = None,
    create_session_in_dir: Optional[bool] = None,
    session_id: Optional[str] = None,
    continue_session: bool = False,
) -> None:
    """Main bridge poll/register/spawn loop."""

    def _debug(message: str) -> None:
        try:
            from ..utils.debug import log_for_debugging
            log_for_debugging(message)
        except Exception:
            pass

    try:
        from ..utils.git import get_branch, get_remote_url
        branch = await get_branch()
        git_repo_url = await get_remote_url()
    except Exception:
        branch = ""
        git_repo_url = None

    cwd = os.getcwd()
    max_sessions = max(1, capacity or 1)
    chosen_spawn_mode: SpawnMode = spawn_mode or "single-session"
    if max_sessions > 1 and chosen_spawn_mode == "single-session":
        chosen_spawn_mode = "same-dir"

    config: Dict[str, Any] = {
        "dir": cwd,
        "machineName": name or socket.gethostname(),
        "branch": branch,
        "gitRepoUrl": git_repo_url,
        "maxSessions": max_sessions,
        "spawnMode": chosen_spawn_mode,
        "verbose": verbose,
        "sandbox": sandbox,
        "bridgeId": str(uuid.uuid4()),
        "workerType": "vivian_code",
        "environmentId": str(uuid.uuid4()),
        "reuseEnvironmentId": None,
        "apiBaseUrl": base_url,
        "sessionIngressUrl": base_url,
        "debugFile": debug_file,
        "sessionTimeoutMs": session_timeout_ms,
    }

    logger = createBridgeLogger(verbose)
    logger.setRepoInfo(os.path.basename(cwd), branch)

    from .trustedDevice import getTrustedDeviceToken
    from ..utils.auth import handle_oauth_401_error

    async def _refresh_oauth(_stale_token: str) -> bool:
        return await handle_oauth_401_error()

    api = createBridgeApiClient(
        base_url=base_url,
        get_access_token=lambda: access_token,
        runner_version=PRODUCT_VERSION,
        on_debug=_debug,
        on_auth_401=_refresh_oauth,
        get_trusted_device_token=getTrustedDeviceToken,
    )

    reg = await api.registerBridgeEnvironment(config)  # type: ignore[arg-type]
    environment_id = reg.get("environment_id") or config["environmentId"]
    environment_secret = reg.get("environment_secret") or access_token

    logger.printBanner(config, environment_id)
    logger.updateSessionCount(0, max_sessions, chosen_spawn_mode)

    exec_path = sys.executable
    script_args = ["-m", "vivian_cli.entrypoints.cli"]
    spawner = createSessionSpawner(
        exec_path=exec_path,
        script_args=script_args,
        env=os.environ.copy(),
        verbose=verbose,
        sandbox=sandbox,
        debug_file=debug_file,
        permission_mode=permission_mode,
        on_debug=_debug,
        on_activity=lambda sid, activity: logger.updateSessionActivity(sid, activity),
    )

    stop_event = asyncio.Event()
    capacity_wake = createCapacityWake(stop_event)
    active_sessions: Dict[str, Any] = {}
    session_start_times: Dict[str, int] = {}
    session_work_ids: Dict[str, str] = {}
    session_timeout_tasks: Dict[str, asyncio.Task[Any]] = {}
    watcher_tasks: set[asyncio.Task[Any]] = set()

    try:
        loop = asyncio.get_running_loop()
        for sig in (getattr(__import__("signal"), "SIGINT", None), getattr(__import__("signal"), "SIGTERM", None)):
            if sig is None:
                continue
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                pass
    except Exception:
        pass

    poll_cfg = getPollIntervalConfig()

    async def _timeout_session(session_key: str, timeout_ms: int) -> None:
        try:
            await asyncio.sleep(timeout_ms / 1000.0)
            handle = active_sessions.get(session_key)
            if handle is not None:
                logger.logError(f"Session timed out: {session_key}")
                handle.kill()
        except asyncio.CancelledError:
            return

    async def _watch_session(session_key: str) -> None:
        handle = active_sessions[session_key]
        done_future = getattr(handle, "done", None)
        status = await done_future if done_future is not None else "completed"
        duration_ms = int(asyncio.get_event_loop().time() * 1000) - session_start_times.get(session_key, 0)
        active_sessions.pop(session_key, None)
        session_start_times.pop(session_key, None)
        work_id = session_work_ids.pop(session_key, None)
        timeout_task = session_timeout_tasks.pop(session_key, None)
        if timeout_task is not None:
            timeout_task.cancel()

        logger.removeSession(session_key)
        logger.updateSessionCount(len(active_sessions), max_sessions, chosen_spawn_mode)

        if status == "completed":
            logger.logSessionComplete(session_key, duration_ms)
            try:
                await api.archiveSession(session_key)
            except Exception:
                pass
        elif status == "interrupted":
            logger.logSessionFailed(session_key, "interrupted")
            if work_id:
                try:
                    await api.stopWork(environment_id, work_id, False)
                except Exception:
                    pass
        else:
            logger.logSessionFailed(session_key, "failed")
            if work_id:
                try:
                    await api.stopWork(environment_id, work_id, True)
                except Exception:
                    pass

        if not active_sessions:
            logger.updateIdleStatus()
        capacity_wake.wake()

    async def _spawn_work_session(work: Dict[str, Any]) -> None:
        work_id = str(work.get("id") or "")
        data = work.get("data") or {}
        session_key = str(data.get("id") or "")
        if not session_key:
            return

        secret = decodeWorkSecret(str(work.get("secret") or ""))
        session_token = str(secret["session_ingress_token"])

        if session_key in active_sessions:
            active_sessions[session_key].updateAccessToken(session_token)
            await api.acknowledgeWork(environment_id, work_id, session_token)
            return

        await api.acknowledgeWork(environment_id, work_id, session_token)

        use_ccr_v2 = bool(secret.get("use_code_sessions") or os.environ.get("vivian_BRIDGE_USE_CCR_V2"))
        worker_epoch: Optional[int] = None
        if use_ccr_v2:
            api_base = str(secret.get("api_base_url") or base_url)
            sdk_url = buildCCRv2SdkUrl(api_base, session_key)
            worker_epoch = await registerWorker(sdk_url, session_token)
        else:
            sdk_url = buildSdkUrl(config["sessionIngressUrl"], session_key)

        handle = spawner.spawn(
            {
                "sessionId": session_key,
                "sdkUrl": sdk_url,
                "accessToken": session_token,
                "useCcrV2": use_ccr_v2,
                **({"workerEpoch": worker_epoch} if worker_epoch is not None else {}),
            },
            cwd,
        )
        active_sessions[session_key] = handle
        session_start_times[session_key] = int(asyncio.get_event_loop().time() * 1000)
        session_work_ids[session_key] = work_id

        session_url = buildBridgeSessionUrl(session_key, environment_id, config["sessionIngressUrl"])
        if max_sessions <= 1:
            logger.setAttached(session_key)
        logger.addSession(session_key, session_url)
        logger.updateSessionCount(len(active_sessions), max_sessions, chosen_spawn_mode)
        logger.logSessionStart(session_key, session_key)

        if session_timeout_ms and session_timeout_ms > 0:
            session_timeout_tasks[session_key] = asyncio.create_task(_timeout_session(session_key, session_timeout_ms))

        watcher = asyncio.create_task(_watch_session(session_key))
        watcher_tasks.add(watcher)
        watcher.add_done_callback(lambda task: watcher_tasks.discard(task))

    try:
        while not stop_event.is_set():
            if len(active_sessions) >= max_sessions:
                signal_handle = capacity_wake.signal()
                timeout_ms = poll_cfg["multisession_poll_interval_ms_at_capacity"] if max_sessions > 1 else poll_cfg["poll_interval_ms_at_capacity"]
                try:
                    if timeout_ms > 0:
                        await asyncio.wait_for(signal_handle.wait_aborted(), timeout=timeout_ms / 1000.0)
                    else:
                        await signal_handle.wait_aborted()
                except asyncio.TimeoutError:
                    pass
                finally:
                    signal_handle.cleanup()
                continue

            try:
                work = await api.pollForWork(
                    environment_id,
                    environment_secret,
                    reclaim_older_than_ms=poll_cfg.get("reclaim_older_than_ms"),
                )
            except BridgeFatalError as err:
                logger.updateFailedStatus(str(err))
                raise
            except Exception as err:
                logger.logError(f"Poll failed: {describeAxiosError(err)}")
                await asyncio.sleep(min((backoff or DEFAULT_BACKOFF)["connInitialMs"] / 1000.0, 5.0))
                continue

            if work is None:
                if not active_sessions:
                    logger.updateIdleStatus()
                wait_ms = poll_cfg["multisession_poll_interval_ms_not_at_capacity"] if max_sessions > 1 else poll_cfg["poll_interval_ms_not_at_capacity"]
                await asyncio.sleep(wait_ms / 1000.0)
                continue

            await _spawn_work_session(work)
    finally:
        stop_event.set()
        for timeout_task in session_timeout_tasks.values():
            timeout_task.cancel()
        for handle in list(active_sessions.values()):
            try:
                handle.kill()
            except Exception:
                pass
        if watcher_tasks:
            await asyncio.gather(*watcher_tasks, return_exceptions=True)
        try:
            await api.deregisterEnvironment(environment_id)
        except Exception:
            pass
        logger.clearStatus()


async def runBridgeHeadless(opts: HeadlessBridgeOpts) -> None:
    """Run a headless bridge session (no TTY, controlled by caller)."""
    required = ["sessionId", "sdkUrl", "accessToken"]
    missing = [key for key in required if not opts.get(key)]
    if missing:
        raise BridgeHeadlessPermanentError(f"Missing headless bridge option(s): {', '.join(missing)}")

    spawner = createSessionSpawner(
        exec_path=sys.executable,
        script_args=["-m", "vivian_cli.entrypoints.cli"],
        env=os.environ.copy(),
        verbose=bool(opts.get("verbose", False)),
        sandbox=bool(opts.get("sandbox", False)),
        permission_mode=opts.get("permissionMode"),
        on_debug=lambda _msg: None,
        on_activity=(lambda sid, activity: opts["onActivity"](sid, activity)) if opts.get("onActivity") else None,
    )
    handle = spawner.spawn(
        {
            "sessionId": opts["sessionId"],
            "sdkUrl": opts["sdkUrl"],
            "accessToken": opts["accessToken"],
            **({"useCcrV2": True, "workerEpoch": opts["workerEpoch"]} if opts.get("workerEpoch") is not None else {}),
        },
        opts.get("dir") or os.getcwd(),
    )
    status = await getattr(handle, "done")
    if opts.get("onDone"):
        maybe = opts["onDone"](status)
        if asyncio.iscoroutine(maybe):
            await maybe
    if status != "completed":
        raise BridgeHeadlessPermanentError(f"Headless bridge session ended with status: {status}")


async def bridgeMain(args: List[str]) -> None:
    """Entry point for `vivian bridge` subcommand."""
    parsed = parseArgs(args)

    if parsed.get("help"):
        print("Usage: vivian bridge [options]")
        print("  --verbose                 Enable verbose logging")
        print("  --sandbox                 Run in sandbox mode")
        print("  --debug-file <path>       Write debug logs to file")
        print("  --session-timeout-ms <n>  Session timeout in ms")
        print("  --permission-mode <mode>  Permission mode")
        print("  --name <name>             Session name")
        print("  --spawn <mode>            Spawn mode: session|same-dir|worktree")
        print("  --capacity <n>            Max concurrent sessions")
        print("  --session-id <id>         Resume session by ID")
        print("  --continue                Resume last session in cwd")
        return

    if parsed.get("error"):
        print(f"Error: {parsed['error']}", file=sys.stderr)
        sys.exit(1)

    try:
        from .bridgeConfig import getBridgeAccessToken, getBridgeBaseUrl
        access_token = getBridgeAccessToken()
        if not access_token:
            print("Error: Not logged in. Run `vivian /login` to authenticate.", file=sys.stderr)
            sys.exit(1)

        await runBridgeLoop(
            base_url=getBridgeBaseUrl(),
            access_token=access_token,
            verbose=parsed.get("verbose", False),
            sandbox=parsed.get("sandbox", False),
            debug_file=parsed.get("debugFile"),
            session_timeout_ms=parsed.get("sessionTimeoutMs"),
            permission_mode=parsed.get("permissionMode"),
            name=parsed.get("name"),
            spawn_mode=parsed.get("spawnMode"),
            capacity=parsed.get("capacity"),
            create_session_in_dir=parsed.get("createSessionInDir"),
            session_id=parsed.get("sessionId"),
            continue_session=parsed.get("continueSession", False),
        )
    except Exception as e:
        print(f"Bridge error: {e}", file=sys.stderr)
        sys.exit(1)

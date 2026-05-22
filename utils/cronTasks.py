"""
Port of src/utils/cronTasks.ts
"""
from __future__ import annotations

from typing import Any, Dict
import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .cron import computeNextCronRun, parseCronExpression


CronTask = Dict[str, Any]
CronFile = Dict[str, Any]
CronJitterConfig = Dict[str, Any]


DEFAULT_CRON_JITTER_CONFIG: CronJitterConfig = {
    'recurringFrac': 0.1,
    'recurringCapMs': 15 * 60 * 1000,
    'oneShotMaxMs': 90 * 1000,
    'oneShotFloorMs': 0,
    'oneShotMinuteMod': 30,
    'recurringMaxAgeMs': 7 * 24 * 60 * 60 * 1000,
}

_SESSION_CRON_TASKS: list[CronTask] = []


def getCronFilePath(dir=None):
    """Path to the cron file. `dir` defaults to getProjectRoot() — pass it
explicitly from contexts that don't run through main.tsx (e.g. the Agent
SDK daemon, which has no bootstrap state)."""
    base = Path(dir) if dir is not None else Path.cwd()
    return str(base / '.vivian' / 'scheduled_tasks.json')


async def readCronTasks(dir=None):
    """Read and parse .vivian/scheduled_tasks.json. Returns an empty task list if the file
is missing, empty, or malformed. Tasks with invalid cron strings are
silently dropped (logged at debug level) so a single bad entry never
blocks the whole file."""
    path = Path(getCronFilePath(dir))
    try:
        raw = path.read_text(encoding='utf-8').strip()
    except FileNotFoundError:
        return []
    except OSError:
        return []

    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    tasks = data.get('tasks') if isinstance(data, dict) else data
    if not isinstance(tasks, list):
        return []
    valid: list[CronTask] = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        cron = task.get('cron')
        if not isinstance(cron, str) or parseCronExpression(cron) is None:
            continue
        valid.append(task)
    return valid


def hasCronTasksSync(dir=None):
    """Sync check for whether the cron file has any valid tasks. Used by
cronScheduler.start() to decide whether to auto-enable. One file read."""
    path = Path(getCronFilePath(dir))
    if not path.exists():
        return False
    try:
        tasks = json.loads(path.read_text(encoding='utf-8') or '{}')
    except Exception:
        return False
    items = tasks.get('tasks') if isinstance(tasks, dict) else tasks
    return isinstance(items, list) and len(items) > 0


async def writeCronTasks(tasks, dir=None):
    """Overwrite .vivian/scheduled_tasks.json with the given tasks. Creates .vivian/ if
missing. Empty task list writes an empty file (rather than deleting) so
the file watcher sees a change event on last-task-removed."""
    path = Path(getCronFilePath(dir))
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: CronFile = {'tasks': list(tasks or [])}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
    return None


async def addCronTask(cron, prompt, recurring, durable, agentId=None, dir=None):
    """Append a task. Returns the generated id. Caller is responsible for having
already validated the cron string (the tool does this via validateInput).

When `durable` is false the task is held in process memory only
(bootstrap/state.ts) — it fires on schedule this session but is never
written to .vivian/scheduled_tasks.json and dies with the process. The
scheduler merges session tasks into its tick loop directly, so no file
change event is needed."""
    task_id = uuid.uuid4().hex[:8]
    task: CronTask = {
        'id': task_id,
        'cron': cron,
        'prompt': prompt,
        'recurring': bool(recurring),
        'durable': bool(durable),
        'createdAt': int(datetime.now(timezone.utc).timestamp() * 1000),
    }
    if agentId is not None:
        task['agentId'] = agentId

    if durable:
        tasks = await readCronTasks(dir)
        tasks.append(task)
        await writeCronTasks(tasks, dir)
    else:
        _SESSION_CRON_TASKS.append(task)
    return task_id


async def removeCronTasks(ids, dir=None):
    """Remove tasks by id. No-op if none match (e.g. another session raced us).
Used for both fire-once cleanup and explicit CronDelete.

When called with `dir` undefined (REPL path), also sweeps the in-memory
session store — the caller doesn't know which store an id lives in.
Daemon callers pass `dir` explicitly; they have no session, and the
`dir !== undefined` guard keeps this function from touching bootstrap
state on that path (tests enforce this)."""
    id_set = {str(item) for item in (ids or [])}
    tasks = await readCronTasks(dir)
    filtered = [task for task in tasks if str(task.get('id')) not in id_set]
    await writeCronTasks(filtered, dir)

    if dir is None:
        _SESSION_CRON_TASKS[:] = [task for task in _SESSION_CRON_TASKS if str(task.get('id')) not in id_set]
    return None


async def markCronTasksFired(ids, firedAt, dir=None):
    """Stamp `lastFiredAt` on the given recurring tasks and write back. Batched
so N fires in one scheduler tick = one read-modify-write, not N. Only
touches file-backed tasks — session tasks die with the process, no point
persisting their fire time. No-op if none of the ids match (task was
deleted between fire and write — e.g. user ran CronDelete mid-tick).

Scheduler lock means at most one process calls this; chokidar picks up
the write and triggers a reload which re-seeds `nextFireAt` from the
just-written `lastFiredAt` — idempotent (same computation, same answer)."""
    id_set = {str(item) for item in (ids or [])}
    if not id_set:
        return None
    tasks = await readCronTasks(dir)
    changed = False
    for task in tasks:
        if str(task.get('id')) in id_set:
            task['lastFiredAt'] = int(firedAt)
            changed = True
    if changed:
        await writeCronTasks(tasks, dir)
    return None


async def listAllCronTasks(dir=None):
    """File-backed tasks + session-only tasks, merged. Session tasks get
`durable: false` so callers can distinguish them. File tasks are
returned as-is (durable undefined → truthy).

Only merges when `dir` is undefined — daemon callers (explicit `dir`)
have no session store to merge with."""
    file_tasks = await readCronTasks(dir)
    if dir is not None:
        return file_tasks
    return [*file_tasks, *[dict(task, durable=False) for task in _SESSION_CRON_TASKS]]


def nextCronRunMs(cron, fromMs):
    """Next fire time in epoch ms for a cron string, strictly after `fromMs`.
Returns null if invalid or no match in the next 366 days."""
    fields = parseCronExpression(cron)
    if fields is None:
        return None
    dt = datetime.fromtimestamp(fromMs / 1000, tz=timezone.utc).astimezone()
    next_run = computeNextCronRun(fields, dt)
    if next_run is None:
        return None
    return int(next_run.timestamp() * 1000)


def jitterFrac(taskId):
    """taskId is an 8-hex-char UUID slice (see {@link addCronTask}) → parse as
u32 → [0, 1). Stable across restarts, uniformly distributed across the
fleet. Non-hex ids (hand-edited JSON) fall back to 0 = no jitter."""
    try:
        frac = int(str(taskId)[:8], 16) / 0x1_0000_0000
    except Exception:
        return 0
    return frac if isinstance(frac, float) and math.isfinite(frac) else 0


def jitteredNextCronRunMs(cron, fromMs, taskId, cfg=DEFAULT_CRON_JITTER_CONFIG):
    """Same as {@link nextCronRunMs}, plus a deterministic per-task delay to
avoid a thundering herd when many sessions schedule the same cron string
(e.g. `0 * * * *` → everyone hits inference at :00).

The delay is proportional to the current gap between fires
({@link CronJitterConfig.recurringFrac}, capped at
{@link CronJitterConfig.recurringCapMs}) so at defaults an hourly task
spreads across [:00, :06) but a per-minute task only spreads by a few
seconds.

Only used for recurring tasks. One-shot tasks use
{@link oneShotJitteredNextCronRunMs} (backward jitter, minute-gated)."""
    t1 = nextCronRunMs(cron, fromMs)
    if t1 is None:
        return None
    t2 = nextCronRunMs(cron, t1)
    if t2 is None:
        return t1
    jitter = min(
        jitterFrac(taskId) * cfg['recurringFrac'] * (t2 - t1),
        cfg['recurringCapMs'],
    )
    return int(t1 + jitter)


def oneShotJitteredNextCronRunMs(cron, fromMs, taskId, cfg=DEFAULT_CRON_JITTER_CONFIG):
    """Same as {@link nextCronRunMs}, minus a deterministic per-task lead time
when the fire time lands on a minute boundary matching
{@link CronJitterConfig.oneShotMinuteMod}.

One-shot tasks are user-pinned ("remind me at 3pm") so delaying them
breaks the contract — but firing slightly early is invisible and spreads
the inference spike from everyone picking the same round wall-clock time.
At defaults (mod 30, max 90 s, floor 0) only :00 and :30 get jitter,
because humans round to the half-hour.

During an incident, ops can push `tengu_kairos_cron_config` with e.g.
`{oneShotMinuteMod: 15, oneShotMaxMs: 300000, oneShotFloorMs: 30000}` to
spread :00/:15/:30/:45 fires across a [t-5min, t-30s] window — every task
gets at least 30 s of lead, so nobody lands on the exact mark.

Checks the computed fire time rather than the cron string so
`0 15 * * *`, step expressions, and `0,30 9 * * *` all get jitter
when they land on a matching minute. Clamped to `fromMs` so a task created
inside its own jitter window doesn't fire before it was created."""
    t1 = nextCronRunMs(cron, fromMs)
    if t1 is None:
        return None
    if datetime.fromtimestamp(t1 / 1000).astimezone().minute % cfg['oneShotMinuteMod'] != 0:
        return t1
    lead = cfg['oneShotFloorMs'] + jitterFrac(taskId) * (cfg['oneShotMaxMs'] - cfg['oneShotFloorMs'])
    return int(max(t1 - lead, fromMs))


def findMissedTasks(tasks, nowMs):
    """A task is "missed" when its next scheduled run (computed from createdAt)
is in the past. Surfaced to the user at startup. Works for both one-shot
and recurring tasks — a recurring task whose window passed while vivian
was down is still "missed"."""
    missed: list[CronTask] = []
    for task in tasks or []:
        if not isinstance(task, dict):
            continue
        anchor = int(task.get('lastFiredAt') or task.get('createdAt') or nowMs)
        next_run = nextCronRunMs(str(task.get('cron', '')), max(anchor - 1, 0))
        if next_run is not None and next_run <= nowMs:
            missed.append(task)
    return missed


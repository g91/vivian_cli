"""
    pass of src/utils/cronScheduler
"""
from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, Dict

from .cron import cronToHuman
from .cronTasks import findMissedTasks, listAllCronTasks, markCronTasksFired, nextCronRunMs, removeCronTasks
from .cronTasksLock import releaseSchedulerLock, tryAcquireSchedulerLock


CronSchedulerOptions = Dict[str, Any]
CronScheduler = Dict[str, Any]

CHECK_INTERVAL_MS = 1000


def isRecurringTaskAged(t, nowMs, maxAgeMs):
    """True when a recurring task was created more than `maxAgeMs` ago and should"""
    if not maxAgeMs:
        return False
    return bool(t.get('recurring')) and not bool(t.get('permanent')) and (nowMs - int(t.get('createdAt') or nowMs)) >= int(maxAgeMs)


def createCronScheduler(options):
    options = options or {}
    on_fire = options['onFire']
    is_loading = options.get('isLoading', lambda: False)
    assistant_mode = bool(options.get('assistantMode', False))
    on_fire_task = options.get('onFireTask')
    on_missed = options.get('onMissed')
    dir_value = options.get('dir')
    lock_identity = options.get('lockIdentity')
    get_jitter_config = options.get('getJitterConfig')
    is_killed = options.get('isKilled')
    filter_fn = options.get('filter')

    stop_event = threading.Event()
    started = False
    worker: threading.Thread | None = None
    next_fire_at: dict[str, int] = {}
    missed_asked: set[str] = set()
    lock_opts = {'dir': dir_value, 'lockIdentity': lock_identity} if dir_value or lock_identity else None
    is_owner = False

    def _run(coro):
        return asyncio.run(coro)

    def _task_allowed(task: dict[str, Any]) -> bool:
        return bool(filter_fn(task)) if callable(filter_fn) else True

    def _effective_anchor(task: dict[str, Any], now_ms: int) -> int:
        return int(task.get('lastFiredAt') or task.get('createdAt') or now_ms)

    def _load(initial: bool) -> list[dict[str, Any]]:
        tasks = _run(listAllCronTasks(dir_value))
        tasks = [task for task in tasks if isinstance(task, dict) and _task_allowed(task)]
        if initial:
            now_ms = int(time.time() * 1000)
            missed = [task for task in findMissedTasks(tasks, now_ms) if not task.get('recurring') and task.get('id') not in missed_asked]
            if missed:
                for task in missed:
                    missed_asked.add(str(task.get('id')))
                if callable(on_missed):
                    on_missed(missed)
                else:
                    on_fire(buildMissedTaskNotification(missed))
                _run(removeCronTasks([task['id'] for task in missed if task.get('id')], dir_value))
                tasks = [task for task in tasks if str(task.get('id')) not in {str(item.get('id')) for item in missed}]
        return tasks

    def _check(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if callable(is_killed) and is_killed():
            return tasks
        if callable(is_loading) and is_loading() and not assistant_mode:
            return tasks
        now_ms = int(time.time() * 1000)
        fired_recurring: list[str] = []
        remaining: list[dict[str, Any]] = []
        max_age_ms = int((get_jitter_config() or {}).get('recurringMaxAgeMs', 7 * 24 * 60 * 60 * 1000)) if callable(get_jitter_config) else 7 * 24 * 60 * 60 * 1000

        for task in tasks:
            task_id = str(task.get('id'))
            anchor = _effective_anchor(task, now_ms)
            next_run = next_fire_at.get(task_id)
            if next_run is None:
                next_run = nextCronRunMs(str(task.get('cron', '')), max(anchor - 1, 0))
                if next_run is None:
                    continue
                next_fire_at[task_id] = next_run
            if now_ms < next_run:
                remaining.append(task)
                continue

            if callable(on_fire_task):
                on_fire_task(task)
            else:
                on_fire(str(task.get('prompt', '')))

            aged = isRecurringTaskAged(task, now_ms, max_age_ms)
            if task.get('recurring') and not aged:
                task['lastFiredAt'] = now_ms
                next_fire_at[task_id] = nextCronRunMs(str(task.get('cron', '')), now_ms) or (now_ms + 60_000)
                fired_recurring.append(task_id)
                remaining.append(task)
                continue

            next_fire_at.pop(task_id, None)
            if is_owner and task.get('id'):
                _run(removeCronTasks([task['id']], dir_value))

        if is_owner and fired_recurring:
            _run(markCronTasksFired(fired_recurring, now_ms, dir_value))
        return remaining

    def _loop() -> None:
        nonlocal is_owner
        if lock_opts:
            try:
                is_owner = bool(_run(tryAcquireSchedulerLock(lock_opts)))
            except Exception:
                is_owner = False
        else:
            is_owner = True
        tasks = _load(initial=True)
        while not stop_event.is_set():
            tasks = _load(initial=False)
            tasks = _check(tasks)
            stop_event.wait(CHECK_INTERVAL_MS / 1000.0)
        if lock_opts and is_owner:
            try:
                _run(releaseSchedulerLock(lock_opts))
            except Exception:
                pass

    def start() -> None:
        nonlocal worker, started
        if started:
            return
        started = True
        stop_event.clear()
        worker = threading.Thread(target=_loop, daemon=True, name='CronScheduler')
        worker.start()

    def stop() -> None:
        stop_event.set()

    def getNextFireTime() -> int | None:
        if not next_fire_at:
            return None
        return min(next_fire_at.values())

    return {
        'start': start,
        'stop': stop,
        'getNextFireTime': getNextFireTime,
    }


def buildMissedTaskNotification(missed):
    """Build the missed-task notification text. Guidance precedes the task list"""
    tasks = [task for task in (missed or []) if isinstance(task, dict)]
    if not tasks:
        return 'You have missed scheduled tasks.'
    lines = ['vivian was not running when these one-shot scheduled tasks were due:']
    for task in tasks:
        cron = str(task.get('cron', ''))
        prompt = str(task.get('prompt', '')).strip()
        lines.append(f"- {task.get('id', '')}: {cronToHuman(cron)} -> {prompt}")
    lines.append('Review them and decide whether to rerun or recreate them.')
    return '\n'.join(lines)


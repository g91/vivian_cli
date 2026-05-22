"""Turn-scoped workload context — mirrors src/utils/workloadContext.ts"""
from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import Literal, Optional

Workload = Literal["cron"]
WORKLOAD_CRON: Workload = "cron"

_workload_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "workload", default=None
)


def get_workload() -> Optional[str]:
    """Return the current workload tag, or None if not set."""
    return _workload_var.get()


@contextmanager
def run_with_workload(workload: Optional[str]):
    """Context manager that sets the workload tag for the duration of the block.

    Mirrors runWithWorkload() from workloadContext.ts. Uses Python's
    contextvars.ContextVar for isolation instead of Node's AsyncLocalStorage.

    Example::

        with run_with_workload("cron"):
            await do_cron_work()
    """
    token = _workload_var.set(workload)
    try:
        yield
    finally:
        _workload_var.reset(token)

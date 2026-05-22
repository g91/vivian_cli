"""Compatibility wrapper for the exact-case pillLabel module."""

from __future__ import annotations

from .pillLabel import getPillLabel, pillNeedsCta


def get_pill_label(task):
    return getPillLabel([task])


def format_task_summary(tasks):
    return getPillLabel(list(tasks))


__all__ = ["format_task_summary", "getPillLabel", "get_pill_label", "pillNeedsCta"]

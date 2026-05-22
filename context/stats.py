"""Stats context — mirrors src/context/stats.tsx."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Optional

RESERVOIR_SIZE = 1024


def percentile(sorted_values: list[float], p: float) -> float:
    index = (p / 100.0) * (len(sorted_values) - 1)
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    if lower == upper:
        return sorted_values[lower]
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (index - lower)


@dataclass
class Histogram:
    reservoir: list[float] = field(default_factory=list)
    count: int = 0
    sum: float = 0.0
    min: float = 0.0
    max: float = 0.0


class StatsContext:
    """Stats tracking context."""

    def __init__(self) -> None:
        self._metrics: dict[str, float] = {}
        self._histograms: dict[str, Histogram] = {}
        self._sets: dict[str, set[str]] = {}
        self._listeners: list[Callable] = []

    def increment(self, name: str, value: float = 1) -> None:
        self._metrics[name] = self._metrics.get(name, 0.0) + value
        self._emit(name, self._metrics[name])

    def set(self, name: str, value: float) -> None:
        self._metrics[name] = value
        self._emit(name, value)

    def observe(self, name: str, value: float) -> None:
        histogram = self._histograms.get(name)
        if histogram is None:
            histogram = Histogram(min=value, max=value)
            self._histograms[name] = histogram

        histogram.count += 1
        histogram.sum += value
        histogram.min = min(histogram.min, value)
        histogram.max = max(histogram.max, value)

        if len(histogram.reservoir) < RESERVOIR_SIZE:
            histogram.reservoir.append(value)
        else:
            slot = int(random.random() * histogram.count)
            if slot < RESERVOIR_SIZE:
                histogram.reservoir[slot] = value

        self._emit(name, value)

    def add(self, name: str, value: str) -> None:
        values = self._sets.setdefault(name, set())
        values.add(value)
        self._emit(name, len(values))

    def get(self, key: str) -> float | None:
        return self.getAll().get(key)

    def getAll(self) -> dict[str, float]:
        result = dict(self._metrics)

        for name, histogram in self._histograms.items():
            if histogram.count == 0:
                continue
            result[f"{name}_count"] = float(histogram.count)
            result[f"{name}_min"] = histogram.min
            result[f"{name}_max"] = histogram.max
            result[f"{name}_avg"] = histogram.sum / histogram.count
            sorted_values = sorted(histogram.reservoir)
            result[f"{name}_p50"] = percentile(sorted_values, 50)
            result[f"{name}_p95"] = percentile(sorted_values, 95)
            result[f"{name}_p99"] = percentile(sorted_values, 99)

        for name, values in self._sets.items():
            result[name] = float(len(values))

        return result

    def subscribe(self, callback: Callable) -> Callable:
        self._listeners.append(callback)

        def unsubscribe() -> None:
            if callback in self._listeners:
                self._listeners.remove(callback)

        return unsubscribe

    def _emit(self, key: str, value: float) -> None:
        for cb in list(self._listeners):
            cb(key, value)


_stats_instance: Optional[StatsContext] = None


def createStatsStore() -> StatsContext:
    return StatsContext()


def useStats() -> StatsContext:
    global _stats_instance
    if _stats_instance is None:
        _stats_instance = createStatsStore()
    return _stats_instance


def useCounter(name: str) -> Callable[[float], None]:
    store = useStats()
    return lambda value=1: store.increment(name, value)


def useGauge(name: str) -> Callable[[float], None]:
    store = useStats()
    return lambda value: store.set(name, value)


def useTimer(name: str) -> Callable[[float], None]:
    store = useStats()
    return lambda value: store.observe(name, value)


def useSet(name: str) -> Callable[[str], None]:
    store = useStats()
    return lambda value: store.add(name, value)


create_stats_store = createStatsStore
use_stats = useStats
use_counter = useCounter
use_gauge = useGauge
use_timer = useTimer
use_set = useSet

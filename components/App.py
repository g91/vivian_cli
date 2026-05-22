"""Top-level app component wrapper — mirrors src/components/App.tsx."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..context.fpsMetrics import FpsMetricsProvider
from ..context.stats import StatsContext, createStatsStore
from ..state.AppState import AppState, AppStateProvider
from ..state.onChangeAppState import onChangeAppState


@dataclass(slots=True)
class AppProps:
    getFpsMetrics: Callable[[], Any]
    initialState: AppState
    children: Any
    stats: StatsContext | None = None


def App(props: AppProps) -> Any:
    stats_store = props.stats if props.stats is not None else createStatsStore()
    with FpsMetricsProvider(getFpsMetrics=props.getFpsMetrics):
        with AppStateProvider(
            initialState=props.initialState,
            onChangeAppStateCallback=lambda change: onChangeAppState(
                newState=change["newState"],
                oldState=change["oldState"],
            ),
        ):
            return {
                "type": "App",
                "stats": stats_store,
                "children": props.children,
            }


__all__ = ["App", "AppProps"]
"""Project onboarding state mirroring src/projectOnboardingState.ts."""

from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .utils.cwd import get_cwd


@dataclass(frozen=True)
class Step:
    key: str
    text: str
    isComplete: bool
    isCompletable: bool
    isEnabled: bool


_ONBOARDING_CACHE: dict[str, bool] = {}


def _project_root() -> Path:
    return Path(get_cwd()).resolve()


def _project_state_path() -> Path:
    return _project_root() / ".vivian" / "project_config.json"


def _read_project_config() -> dict[str, Any]:
    path = _project_state_path()
    try:
        return __import__("json").loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {
            "hasCompletedProjectOnboarding": False,
            "projectOnboardingSeenCount": 0,
        }
    except Exception:
        return {
            "hasCompletedProjectOnboarding": False,
            "projectOnboardingSeenCount": 0,
        }


def _save_project_config(updater):
    current = _read_project_config()
    updated = updater(dict(current)) if callable(updater) else dict(updater)
    path = _project_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(__import__("json").dumps(updated, indent=2, sort_keys=True), encoding="utf-8")


def _is_dir_empty(path: Path) -> bool:
    try:
        return not any(path.iterdir())
    except FileNotFoundError:
        return True


def getSteps() -> list[Step]:
    cwd = _project_root()
    has_vivian_md = (cwd / "vivian.md").exists()
    is_workspace_dir_empty = _is_dir_empty(cwd)

    return [
        Step(
            key="workspace",
            text="Ask vivian to create a new app or clone a repository",
            isComplete=False,
            isCompletable=True,
            isEnabled=is_workspace_dir_empty,
        ),
        Step(
            key="vivianmd",
            text="Run /init to create a vivian.md file with instructions for vivian",
            isComplete=has_vivian_md,
            isCompletable=True,
            isEnabled=not is_workspace_dir_empty,
        ),
    ]


def isProjectOnboardingComplete() -> bool:
    return all(
        step.isComplete
        for step in getSteps()
        if step.isCompletable and step.isEnabled
    )


def maybeMarkProjectOnboardingComplete() -> None:
    if _read_project_config().get("hasCompletedProjectOnboarding"):
        return
    if isProjectOnboardingComplete():
        _save_project_config(
            lambda current: {
                **current,
                "hasCompletedProjectOnboarding": True,
            }
        )
        _ONBOARDING_CACHE.pop(str(_project_root()), None)


def shouldShowProjectOnboarding() -> bool:
    cache_key = str(_project_root())
    if cache_key in _ONBOARDING_CACHE:
        return _ONBOARDING_CACHE[cache_key]

    project_config = _read_project_config()
    result = not (
        project_config.get("hasCompletedProjectOnboarding")
        or project_config.get("projectOnboardingSeenCount", 0) >= 4
        or os.environ.get("IS_DEMO")
    ) and not isProjectOnboardingComplete()
    _ONBOARDING_CACHE[cache_key] = result
    return result


def incrementProjectOnboardingSeenCount() -> None:
    _save_project_config(
        lambda current: {
            **current,
            "projectOnboardingSeenCount": current.get("projectOnboardingSeenCount", 0) + 1,
        }
    )
    _ONBOARDING_CACHE.pop(str(_project_root()), None)


def get_steps() -> list[dict[str, Any]]:
    return [asdict(step) for step in getSteps()]


is_project_onboarding_complete = isProjectOnboardingComplete
maybe_mark_project_onboarding_complete = maybeMarkProjectOnboardingComplete
should_show_project_onboarding = shouldShowProjectOnboarding
increment_project_onboarding_seen_count = incrementProjectOnboardingSeenCount
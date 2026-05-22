"""Port of src/utils/swarm/It2SetupPrompt.tsx.

Python does not mirror the React/Ink UI component directly, so this module
provides a small async controller that drives the same setup state machine and
returns structured prompt data for callers.
"""
from __future__ import annotations

from typing import Any, Dict

from .backends.it2Setup import (
    detectPythonPackageManager,
    getPythonApiInstructions,
    installIt2,
    markIt2SetupComplete,
    setPreferTmuxOverIterm2,
    verifyIt2Setup,
)


SetupStep = str
Props = Dict[str, Any]


async def It2SetupPrompt(t0):
    """Advance or render the iTerm2 setup flow.

    Accepted input keys:
    - ``tmuxAvailable``: bool
    - ``step``: current setup step, defaults to ``initial``
    - ``action``: one of ``install``, ``retry``, ``verify``, ``tmux``, ``cancel``
    - ``packageManager``: optional cached package manager
    - ``error``: optional current error string

    Returns a dict containing the next step, any terminal result, prompt text,
    and the currently available options.
    """
    props = dict(t0 or {})
    step = str(props.get("step") or "initial")
    action = props.get("action")
    tmux_available = bool(props.get("tmuxAvailable"))
    package_manager = props.get("packageManager")
    error = props.get("error")

    if package_manager is None:
        package_manager = await detectPythonPackageManager()

    if action in {"install", "retry"}:
        if not package_manager:
            step = "failed"
            error = "No Python package manager found (uvx, pipx, or pip)"
        else:
            install_result = await installIt2(str(package_manager))
            if install_result.get("success"):
                step = "api-instructions"
                error = None
            else:
                step = "install-failed"
                error = install_result.get("error") or "Installation failed"
    elif action == "verify":
        verify_result = await verifyIt2Setup()
        if verify_result.get("success"):
            markIt2SetupComplete()
            step = "success"
            error = None
            return _build_state(step, tmux_available, package_manager, error, result="installed")
        step = "failed"
        error = verify_result.get("error") or "Verification failed"
    elif action == "tmux":
        setPreferTmuxOverIterm2(True)
        return _build_state(step, tmux_available, package_manager, error, result="use-tmux")
    elif action == "cancel":
        return _build_state(step, tmux_available, package_manager, error, result="cancelled")

    return _build_state(step, tmux_available, package_manager, error)


def _build_state(
    step: SetupStep,
    tmux_available: bool,
    package_manager: str | None,
    error: str | None,
    *,
    result: str | None = None,
) -> Dict[str, Any]:
    state: Dict[str, Any] = {
        "title": "iTerm2 Split Pane Setup",
        "step": step,
        "packageManager": package_manager,
        "error": error,
        "result": result,
        "options": _options_for_step(step, tmux_available, package_manager),
        "body": _body_for_step(step, tmux_available, package_manager, error),
    }
    if step == "api-instructions":
        instructions = getPythonApiInstructions()
        state["instructions"] = instructions
        state["renderedInstructions"] = [_temp(line, index) for index, line in enumerate(instructions)]
    return state


def _options_for_step(step: SetupStep, tmux_available: bool, package_manager: str | None) -> list[Dict[str, str]]:
    if step == "initial":
        options = [
            {
                "label": "Install it2 now",
                "value": "install",
                "description": (
                    f"Uses {package_manager} to install the it2 CLI tool"
                    if package_manager
                    else "Requires Python (uvx, pipx, or pip)"
                ),
            }
        ]
        if tmux_available:
            options.append(
                {
                    "label": "Use tmux instead",
                    "value": "tmux",
                    "description": "Opens teammates in a separate tmux session",
                }
            )
        options.append(
            {
                "label": "Cancel",
                "value": "cancel",
                "description": "Skip teammate spawning for now",
            }
        )
        return options

    if step == "install-failed":
        return _retry_options(tmux_available, retry_description="Retry the installation")

    if step == "failed":
        return _retry_options(tmux_available, retry_description="Verify the connection again")

    if step == "api-instructions":
        return [{"label": "Verify setup", "value": "verify", "description": "Verify iTerm2 Python API connectivity"}]

    return []


def _retry_options(tmux_available: bool, *, retry_description: str) -> list[Dict[str, str]]:
    options = [
        {
            "label": "Try again",
            "value": "retry",
            "description": retry_description,
        }
    ]
    if tmux_available:
        options.append(
            {
                "label": "Use tmux instead",
                "value": "tmux",
                "description": "Falls back to tmux for teammate panes",
            }
        )
    options.append(
        {
            "label": "Cancel",
            "value": "cancel",
            "description": "Skip teammate spawning for now",
        }
    )
    return options


def _body_for_step(step: SetupStep, tmux_available: bool, package_manager: str | None, error: str | None) -> str:
    if step == "initial":
        lines = [
            "To use native iTerm2 split panes for teammates, you need the it2 CLI tool.",
            "This enables teammates to appear as split panes within your current window.",
        ]
        if not package_manager:
            lines.append("No Python package manager was detected yet.")
        elif tmux_available:
            lines.append("tmux is available as a fallback.")
        return "\n".join(lines)

    if step == "installing":
        return f"Installing it2 using {package_manager or 'a detected package manager'}..."

    if step == "install-failed":
        manual = (
            "uv tool install it2"
            if package_manager == "uvx"
            else "pipx install it2"
            if package_manager == "pipx"
            else "pip install --user it2"
        )
        body = ["Installation failed"]
        if error:
            body.append(str(error))
        body.append(f"You can try installing manually: {manual}")
        return "\n".join(body)

    if step == "api-instructions":
        return "\n".join(getPythonApiInstructions() + ["", "Run verify when ready."])

    if step == "verifying":
        return "Verifying it2 can communicate with iTerm2..."

    if step == "success":
        return "iTerm2 split pane support is ready. Teammates will now appear as split panes."

    if step == "failed":
        body = ["Verification failed"]
        if error:
            body.append(str(error))
        body.extend(
            [
                "Make sure:",
                "- Python API is enabled in iTerm2 preferences",
                "- You may need to restart iTerm2 after enabling",
            ]
        )
        return "\n".join(body)

    return ""


def _temp(line, i):
    _ = i
    return str(line)


it2_setup_prompt = It2SetupPrompt
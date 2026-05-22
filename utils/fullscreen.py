"""
Port of src/utils/fullscreen.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import subprocess
import asyncio
import glob
import platform

from ..bootstrap.state import getIsInteractive
from .debug import logForDebugging
from .envUtils import is_env_defined_falsy, is_env_truthy
from .execFileNoThrow import exec_file_no_throw


loggedTmuxCcDisable = False
checkedTmuxMouseHint = False
tmuxControlModeProbed = None


def isTmuxControlModeEnvHeuristic():
    """Env-var heuristic for iTerm2's tmux integration mode (`tmux -CC` / `tmux -2CC`).

In `-CC` mode, iTerm2 renders tmux panes as native splits — tmux runs
as a server (TMUX is set) but iTerm2 is the actual terminal emulator
for each pane, so TERM_PROGRAM stays `iTerm.app` and TERM is iTerm2's
default (xterm-*). Contrast with regular tmux-inside-iTerm2, where tmux
overwrites TERM_PROGRAM to `tmux` and sets TERM to screen-* or tmux-*.

This heuristic has known holes (SSH often doesn't propagate TERM_PROGRAM;
.tmux.conf can override TERM) — probeTmuxControlModeSync() is the
authoritative backstop. Kept as a zero-subprocess fast path."""
    if not os.environ.get('TMUX'):
        return False
    if os.environ.get('TERM_PROGRAM') != 'iTerm.app':
        return False
    term = os.environ.get('TERM', '')
    return not term.startswith('screen') and not term.startswith('tmux')


def probeTmuxControlModeSync():
    """Sync one-shot probe: asks tmux directly whether this client is in control
mode via `#{client_control_mode}`. Runs on first isTmuxControlMode() call
when the env heuristic can't decide; result is cached.

Sync (spawnSync) because the answer gates whether we enter fullscreen — an
async probe raced against React render and lost: coder-tmux (ssh → tmux -CC
on a remote box) doesn't propagate TERM_PROGRAM, so the env heuristic missed,
and by the time the async probe resolved we'd already entered alt-screen with
mouse tracking enabled. Mouse wheel is dead in iTerm2's -CC integration, so
users couldn't scroll at all.

Cost: one ~5ms subprocess, only when $TMUX is set AND $TERM_PROGRAM is unset
(the SSH-into-tmux case). Local iTerm2 -CC and non-tmux paths skip the spawn.

The TMUX env check MUST come first — without it, display-message would
query whatever tmux server happens to be running rather than our client."""
    global tmuxControlModeProbed

    tmuxControlModeProbed = isTmuxControlModeEnvHeuristic()
    if tmuxControlModeProbed:
        return
    if not os.environ.get('TMUX'):
        return
    if os.environ.get('TERM_PROGRAM'):
        return

    try:
        result = subprocess.run(
            ['tmux', 'display-message', '-p', '#{client_control_mode}'],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except Exception:
        return

    if result.returncode != 0:
        return
    tmuxControlModeProbed = result.stdout.strip() == '1'


def isTmuxControlMode():
    """True when running under `tmux -CC` (iTerm2 integration mode).

The alt-screen / mouse-tracking path in fullscreen mode is unrecoverable
in -CC mode (double-click corrupts terminal state; mouse wheel is dead),
so callers auto-disable fullscreen.

Lazily probes tmux on first call when the env heuristic can't decide."""
    if tmuxControlModeProbed is None:
        probeTmuxControlModeSync()
    return bool(tmuxControlModeProbed)


def _resetTmuxControlModeProbeForTesting():
    global tmuxControlModeProbed, loggedTmuxCcDisable
    tmuxControlModeProbed = None
    loggedTmuxCcDisable = False


def isFullscreenEnvEnabled():
    """Runtime env-var check only. Ants default to on (vivian_CODE_NO_FLICKER=0
to opt out); external users default to off (vivian_CODE_NO_FLICKER=1 to
opt in)."""
    global loggedTmuxCcDisable

    if is_env_defined_falsy(os.environ.get('vivian_CODE_NO_FLICKER')):
        return False
    if is_env_truthy(os.environ.get('vivian_CODE_NO_FLICKER')):
        return True
    if isTmuxControlMode():
        if not loggedTmuxCcDisable:
            loggedTmuxCcDisable = True
            logForDebugging(
                'fullscreen disabled: tmux -CC (iTerm2 integration mode) detected · set vivian_CODE_NO_FLICKER=1 to override'
            )
        return False
    return os.environ.get('USER_TYPE') == 'ant'


def isMouseTrackingEnabled():
    """Whether fullscreen mode should enable SGR mouse tracking (DEC 1000/1002/1006).
Set vivian_CODE_DISABLE_MOUSE=1 to keep alt-screen + virtualized scroll
(keyboard PgUp/PgDn/Ctrl+Home/End still work) but skip mouse capture,
so tmux/kitty/terminal-native copy-on-select keeps working.

Compare with vivian_CODE_NO_FLICKER=0 which is all-or-nothing — it also
disables alt-screen and virtualized scrollback."""
    return not is_env_truthy(os.environ.get('vivian_CODE_DISABLE_MOUSE'))


def isMouseClicksDisabled():
    """Whether mouse click handling is disabled (clicks/drags ignored, wheel still
works). Set vivian_CODE_DISABLE_MOUSE_CLICKS=1 to prevent accidental clicks
from triggering cursor positioning, text selection, or message expansion.

Fullscreen-specific — only reachable when vivian_CODE_NO_FLICKER is active."""
    return is_env_truthy(os.environ.get('vivian_CODE_DISABLE_MOUSE_CLICKS'))


def isFullscreenActive():
    """True when the fullscreen alt-screen layout is actually rendering —
requires an interactive REPL session AND the env var not explicitly
set falsy. Headless paths (--print, SDK, in-process teammates) never
enter fullscreen, so features that depend on alt-screen re-rendering
should gate on this."""
    return getIsInteractive() and isFullscreenEnvEnabled()


async def maybeGetTmuxMouseHint():
    """One-time hint for tmux users in fullscreen with `mouse off`.

tmux's `mouse` option is session-scoped by design — there is no
pane-level equivalent. We used to `tmux set mouse on` when entering
alt-screen so wheel scrolling worked, but that changed mouse behavior
for every sibling pane (vim, less, shell) and leaked on kill-pane or
when multiple CC instances raced on restore. Now we leave tmux state
alone — same as vim/less/htop — and just tell the user their options.

Fire-and-forget from REPL startup. Returns the hint text once per
session if TMUX is set, fullscreen is active, and tmux's current
`mouse` option is off; null otherwise."""
    global checkedTmuxMouseHint

    if not os.environ.get('TMUX'):
        return None
    if not isFullscreenActive() or isTmuxControlMode():
        return None
    if checkedTmuxMouseHint:
        return None
    checkedTmuxMouseHint = True

    result = await exec_file_no_throw(
        'tmux',
        ['show', '-Av', 'mouse'],
        cwd=None,
        timeout=2,
    )
    if result.get('code') != 0 or str(result.get('stdout', '')).strip() == 'on':
        return None
    return "tmux detected · scroll with PgUp/PgDn · or add 'set -g mouse on' to ~/.tmux.conf for wheel scroll"


def _resetForTesting():
    global loggedTmuxCcDisable, checkedTmuxMouseHint
    loggedTmuxCcDisable = False
    checkedTmuxMouseHint = False


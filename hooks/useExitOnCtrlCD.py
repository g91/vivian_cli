"""Exit on Ctrl-C/Ctrl-D handler — mirrors src/hooks/useExitOnCtrlCD.ts."""
from __future__ import annotations
from typing import Callable, Any

class ExitState:
    def __init__(self, pending: bool = False, keyName: str | None = None):
        self.pending = pending
        self.keyName = keyName

def useExitOnCtrlCD(
    onInterrupt: Callable[[], bool] | None = None,
    onExit: Callable[[], None] | None = None,
    isActive: bool = True,
) -> dict[str, Any]:
    """Handle Ctrl+C and Ctrl+D for graceful exit."""
    state = ExitState(pending=False, keyName=None)
    
    def handle_interrupt() -> None:
        if onInterrupt and onInterrupt():
            return
        state.pending = True
        state.keyName = 'Ctrl-C'
    
    def handle_exit() -> None:
        if state.pending and state.keyName:
            if onExit:
                onExit()
            else:
                raise KeyboardInterrupt()
        else:
            state.pending = True
            state.keyName = 'Ctrl-D'
    
    return {
        'state': state,
        'handle_interrupt': handle_interrupt,
        'handle_exit': handle_exit,
        'isActive': isActive,
    }

use_exit_on_ctrl_cd = useExitOnCtrlCD

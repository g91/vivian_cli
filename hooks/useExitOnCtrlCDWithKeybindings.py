"""Exit with keybindings — mirrors src/hooks/useExitOnCtrlCDWithKeybindings.ts."""
from __future__ import annotations

def useExitOnCtrlCDWithKeybindings() -> dict:
    """Exit handler integrated with keybindings."""
    return {"pending": False, "keyName": None}

use_exit_on_ctrl_cd_with_keybindings = useExitOnCtrlCDWithKeybindings

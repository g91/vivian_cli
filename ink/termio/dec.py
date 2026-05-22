"""Port of src/ink/termio/dec.ts."""
from .csi import csi

# DEC 2026: Synchronized Output
BSU = csi("?2026h")  # Begin Synchronized Update
ESU = csi("?2026l")  # End Synchronized Update

# Cursor visibility
HIDE_CURSOR = csi("?25l")
SHOW_CURSOR = csi("?25h")

# DECSET/DECRST helpers
def decset(mode: int) -> str:
    return csi(f"?{mode}h")

def decrst(mode: int) -> str:
    return csi(f"?{mode}l")

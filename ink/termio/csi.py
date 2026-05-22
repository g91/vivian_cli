"""Port of src/ink/termio/csi.ts."""
ESC = "\x1b"

def csi(*args: str | int) -> str:
    """Build a CSI sequence: ESC [ + args joined by ;"""
    return f"{ESC}[{';'.join(str(a) for a in args)}"

# Cursor positioning
CURSOR_HOME = csi("H")
CURSOR_UP = lambda n=1: csi(n, "A")
CURSOR_DOWN = lambda n=1: csi(n, "B")
CURSOR_FORWARD = lambda n=1: csi(n, "C")
CURSOR_BACK = lambda n=1: csi(n, "D")

def cursorMove(x: int, y: int) -> str:
    parts = []
    if y != 0:
        parts.append(CURSOR_DOWN(abs(y)) if y > 0 else CURSOR_UP(abs(y)))
    if x != 0:
        parts.append(CURSOR_FORWARD(abs(x)) if x > 0 else CURSOR_BACK(abs(x)))
    return "".join(parts)

def cursorTo(col: int) -> str:
    return csi(col + 1, "G")

# Erase
ERASE_DISPLAY = csi(2, "J")
ERASE_SCREEN = csi(2, "J")
ERASE_SCROLLBACK = csi(3, "J")
ERASE_LINE = csi(2, "K")

def eraseLines(count: int) -> str:
    return "".join(CURSOR_DOWN() + ERASE_LINE for _ in range(count))

# Scroll
SCROLL_UP = lambda n=1: csi(n, "S")
SCROLL_DOWN = lambda n=1: csi(n, "T")

# DECSTBM (set top/bottom margins)
def decstbm(top: int, bottom: int) -> str:
    return csi(top + 1, bottom + 1, "r")

RESET_SCROLL_REGION = csi("r")

# Cursor visibility
HIDE_CURSOR = csi("?25l")
SHOW_CURSOR = csi("?25h")

# SGR reset
SGR_RESET = csi("0m")

cursor_move = cursorMove
cursor_to = cursorTo
erase_lines = eraseLines

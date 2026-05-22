"""Port of src/ink/termio/osc.ts."""
from .ansi import BEL, ESC, SEP, ST

OSC_PREFIX = f"{ESC}]"

class OSC:
    ITERM2 = 1337
    KITTY = 99
    GHOSTTY = 777

class ITERM2:
    PROGRESS = "Progress"

class PROGRESS:
    SET = "Set"
    CLEAR = "Clear"
    ERROR = "Error"
    INDETERMINATE = "Indeterminate"


def osc(code: int, *args: str | int) -> str:
    """Build an OSC sequence: ESC ] code ; args BEL or ST."""
    payload = SEP.join(str(a) for a in args)
    return f"{OSC_PREFIX}{code};{payload}{BEL}"


def link(uri: str, id_param: str = "") -> str:
    """OSC 8 hyperlink. Empty URI closes the link."""
    if not uri:
        return f"{OSC_PREFIX}8;;{BEL}"
    if id_param:
        return f"{OSC_PREFIX}8;id={id_param};{uri}{BEL}"
    return f"{OSC_PREFIX}8;;{uri}{BEL}"


def wrapForMultiplexer(sequence: str) -> str:
    """Wrap an OSC sequence for tmux/screen multiplexer passthrough."""
    tmux = __import__("os").environ.get("TMUX")
    if tmux:
        return f"{ESC}Ptmux;{ESC}{sequence}{ST}"
    screen = __import__("os").environ.get("STY")
    if screen:
        return f"{ESC}P{sequence}{ST}"
    return sequence


wrap_for_multiplexer = wrapForMultiplexer

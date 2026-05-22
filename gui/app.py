"""GUI entrypoint — invoked from cli_main when --gui is passed."""
from __future__ import annotations
import sys
from typing import Any, Optional


def launch_gui(runtime_or_engine: Any, initial_path: str = "") -> int:
    """Start the Qt event loop on the calling thread.

    The engine is the same QueryEngine used by the CLI; the GUI drives it from
    a background asyncio loop (see ai_panel.EngineWorker).
    Returns the Qt exit code.
    """
    from ..utils.debug_log import enable_debug, dlog
    enable_debug()
    dlog("gui: launch_gui start")

    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError as e:
        print(
            "PyQt6 is not installed. Install it with:\n"
            "  pip install PyQt6\n"
            f"({e})",
            file=sys.stderr,
        )
        return 1

    from .main_window import IDEWindow
    from .chat_config import apply_gui_chat_config, load_gui_chat_config
    from .style import DARK_QSS

    runtime = runtime_or_engine if hasattr(runtime_or_engine, "engine") else None
    engine = runtime.engine if runtime is not None else runtime_or_engine

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Vivian IDE")
    app.setStyleSheet(DARK_QSS)

    apply_gui_chat_config(engine, load_gui_chat_config())

    command_handler = getattr(runtime, "execute_slash_command", None) if runtime is not None else None
    window = IDEWindow(engine, initial_path=initial_path, command_handler=command_handler)
    window.show()
    return app.exec()

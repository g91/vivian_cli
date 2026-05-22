#!/usr/bin/env python3
"""UESDKGen.py -- entry point.

Module layout:
  theme.py    -- colour palette + ttk styling
  backends.py -- NativeBackend / VmmBackend / SocketDMABackend
  reader.py   -- UE3Reader + PatternScanner
  profiles.py -- GAME_PROFILES (20 UE3 games)
  codegen.py  -- generate_sdk() C++ and Python
  app.py      -- UESDKGenApp GUI
"""
from __future__ import annotations
import sys


def main() -> None:
    if sys.platform != "win32":
        print("UESDKGen requires Windows.")
        sys.exit(1)
    try:
        from .app import UESDKGenApp
    except ImportError:
        import pathlib as _pl
        _here = str(_pl.Path(__file__).resolve().parent)
        if _here not in sys.path:
            sys.path.insert(0, _here)
        from app import UESDKGenApp  # type: ignore[no-redef]
    UESDKGenApp().mainloop()


if __name__ == "__main__":
    main()

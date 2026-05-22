"""Vivian Desktop Web GUI — cyberpunk Windows 7-style desktop in the browser.

Entry point: ``launch_desktop_gui(engine, host="127.0.0.1", port=7979)``
"""
from .server import launch_desktop_gui

__all__ = ["launch_desktop_gui"]

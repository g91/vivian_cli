"""Web-based GUI for Vivian — mirrors the Qt IDE in the browser.

Entry point: ``launch_web_gui(engine, host="127.0.0.1", port=7878)``.
"""
from .server import launch_web_gui

__all__ = ["launch_web_gui"]

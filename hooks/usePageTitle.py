"""Page title — mirrors src/hooks/usePageTitle.ts.

In Python, this sets the terminal window title and also tracks the current page/session
title for the CLI session. Similar to React's document.title manipulation.
"""
from __future__ import annotations
import os
import sys
from typing import Optional

# Track current title in session
_current_title: Optional[str] = None
_original_title: Optional[str] = None

def _set_terminal_title(title: str) -> None:
    """Set the terminal window title using ANSI escape sequences."""
    try:
        # Most terminals support this escape sequence
        if sys.stdout.isatty():
            # Set both icon name and window title
            sys.stdout.write(f"\033]0;{title}\007")
            sys.stdout.flush()
    except Exception:
        pass  # Silently ignore if terminal doesn't support title setting

def usePageTitle(title: str) -> None:
    """Set the page/window title for the current session.
    
    Updates the terminal window title and tracks it for the current CLI session.
    In a browser context, this would update document.title; in CLI, it updates
    the terminal emulator's window title.
    
    Args:
        title: The title to set for the current page/session
    """
    global _current_title, _original_title
    
    # Save original title on first call
    if _original_title is None and sys.stdout.isatty():
        # Try to get current title (not always possible)
        _original_title = os.environ.get('TERM_PROGRAM_VERSION', 'Vivian CLI')
    
    _current_title = title
    _set_terminal_title(title)

def get_page_title() -> Optional[str]:
    """Get the current page/window title.
    
    Returns:
        The currently set title, or None if not set
    """
    return _current_title

def reset_page_title() -> None:
    """Reset the terminal title to its original value."""
    global _current_title, _original_title
    
    if _original_title:
        _set_terminal_title(_original_title)
    else:
        _set_terminal_title('Vivian CLI')
    
    _current_title = None

use_page_title = usePageTitle

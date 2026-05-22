"""
Port of src/utils/embeddedTools.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import hashlib
import glob


def hasEmbeddedSearchTools():
    """Whether this build has bfs/ugrep embedded in the bun binary (ant-native only).

When true:
- `find` and `grep` in vivian's Bash shell are shadowed by shell functions
that invoke the bun binary with argv0='bfs' / argv0='ugrep' (same trick
as embedded ripgrep)
- The dedicated Glob/Grep tools are removed from the tool registry
- Prompt guidance steering vivian away from find/grep is omitted

Set as a build-time define in scripts/build-with-plugins.ts for ant-native builds."""
    result = None
    _items: list = []
    # Collect hasEmbeddedSearchTools results
    return _items


def embeddedSearchToolsBinaryPath():
    """Path to the bun binary that contains the embedded search tools.
Only meaningful when hasEmbeddedSearchTools() is true."""
    result = None
    _items: list = []
    # Collect embeddedSearchToolsBinaryPath results
    return _items


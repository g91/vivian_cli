"""
Port of src/utils/swarm/backends/types.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import hashlib
import time
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
import socket


BackendType = str
PaneBackendType = str
PaneId = str
CreatePaneResult = Dict[str, Any]
PaneBackend = Dict[str, Any]
BackendDetectionResult = Dict[str, Any]
TeammateIdentity = Dict[str, Any]
TeammateSpawnConfig = Union[Any, str, str]
TeammateSpawnResult = Dict[str, Any]
TeammateMessage = Dict[str, Any]
TeammateExecutor = Dict[str, Any]


def isPaneBackend(type):
    """Type guard to check if a backend type uses terminal panes."""
    return type == 'tmux' or type == 'iterm2'


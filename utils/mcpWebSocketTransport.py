"""
Port of src/utils/mcpWebSocketTransport.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import json
import asyncio
import hashlib
import glob
from dataclasses import dataclass, field
import socket
import struct


WebSocketLike = Dict[str, Any]


class WebSocketTransport:
    def __init__(self, opened=None, onclose=None, onerror=None, onmessage=None):
        self.opened = opened
        self.onclose = onclose
        self.onerror = onerror
        self.onmessage = onmessage



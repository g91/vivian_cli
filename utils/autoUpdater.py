"""
Port of src/utils/autoUpdater.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import json
import asyncio
import hashlib
import time
from datetime import datetime, timezone, timedelta
import glob
import urllib.request
import urllib.parse


class AutoUpdaterError(Exception):
    def __init__(self, channel=None, specificVersion=None):
        super().__init__(channel or specificVersion)
        self.channel = channel
        self.specificVersion = specificVersion



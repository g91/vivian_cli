"""
Port of src/utils/telemetry/instrumentation.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import json
import asyncio
import time
from datetime import datetime, timezone, timedelta
import glob
import platform
import ssl


class TelemetryTimeoutError(Exception):
    def __init__(self, resource=None):
        super().__init__(resource)
        self.resource = resource



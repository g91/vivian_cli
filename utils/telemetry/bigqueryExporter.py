"""
Port of src/utils/telemetry/bigqueryExporter.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import json
import asyncio
import time
from datetime import datetime, timezone, timedelta
import urllib.request
import urllib.parse
import struct


DataPoint = Dict[str, Any]
Metric = Dict[str, Any]
InternalMetricsPayload = Dict[str, Any]


class BigQueryMetricsExporter:
    def __init__(self, endpoint=None, timeout=None, pendingExports=None, metrics=None, resultCallback=None, attributes=None):
        self.endpoint = endpoint
        self.timeout = timeout
        self.pendingExports = pendingExports
        self.metrics = metrics
        self.resultCallback = resultCallback
        self.attributes = attributes



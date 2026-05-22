"""Port of src/utils/bash/specs/index.ts"""
from __future__ import annotations
from typing import Any, List, Dict

from .alias import alias
from .nohup import nohup
from .pyright import pyright
from .sleep import sleep
from .srun import srun
from .time import time
from .timeout import timeout

specs: List[Dict[str, Any]] = [
    pyright,
    timeout,
    sleep,
    alias,
    nohup,
    time,
    srun,
]

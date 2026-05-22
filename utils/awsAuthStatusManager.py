"""
Port of src/utils/awsAuthStatusManager.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import hashlib


AwsAuthStatus = Dict[str, Any]


class AwsAuthStatusManager:
    def __init__(self, instance=None):
        self.instance = instance



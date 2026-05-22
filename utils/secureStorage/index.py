"""
Port of src/utils/secureStorage/index.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import platform


def getSecureStorage():
    """Get the appropriate secure storage implementation for the current platform"""
    if process.platform == 'darwin':
        return createFallbackStorage(macOsKeychainStorage, plainTextStorage)
    # TODO: add libsecret support for Linux
    return plainTextStorage


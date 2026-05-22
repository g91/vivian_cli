"""Port of src/hooks/useAfterFirstRender.ts."""
from __future__ import annotations

import os
import sys
import time

from ..utils.envUtils import is_env_truthy


def useAfterFirstRender() -> None:
    if (
        os.environ.get('USER_TYPE') == 'ant'
        and is_env_truthy(os.environ.get('vivian_CODE_EXIT_AFTER_FIRST_RENDER'))
    ):
        sys.stderr.write(f"\nStartup time: {round(time.monotonic() * 1000)}ms\n")
        raise SystemExit(0)

"""Immediate command gate — mirrors src/utils/immediateCommand.ts"""
from __future__ import annotations

import os


def should_inference_config_command_be_immediate() -> bool:
    """Whether inference-config commands (/model, /fast, /effort) should execute
    immediately during a running query rather than waiting for the turn to finish.
    """
    return os.environ.get("USER_TYPE") == "ant"

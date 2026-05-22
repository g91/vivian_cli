"""Argument substitution — mirrors src/utils/argumentSubstitution.ts"""
from __future__ import annotations
import re

def substitute_arguments(template: str, args: dict[str, str]) -> str:
    """Replace {{key}} placeholders with values from args."""
    def replace(m: re.Match) -> str:
        return args.get(m.group(1), m.group(0))
    return re.sub(r"\{\{(\w+)\}\}", replace, template)

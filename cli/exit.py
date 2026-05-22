"""CLI exit helpers — mirrors src/cli/exit.ts.

Consolidates the print-then-exit pattern for CLI subcommand handlers.
``cli_error`` writes to stderr and exits with code 1.
``cli_ok`` writes to stdout and exits with code 0.
Both are typed ``-> NoReturn`` so type-checkers narrow control flow at call sites.
"""
from __future__ import annotations

import sys
from typing import NoReturn, Optional


def cli_error(msg: Optional[str] = None) -> NoReturn:
    """Write an error message to stderr (if given) and exit with code 1."""
    if msg:
        print(msg, file=sys.stderr)
    sys.exit(1)


def cli_ok(msg: Optional[str] = None) -> NoReturn:
    """Write a message to stdout (if given) and exit with code 0."""
    if msg:
        sys.stdout.write(msg + "\n")
        sys.stdout.flush()
    sys.exit(0)

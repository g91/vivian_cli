"""Peer address parsing — mirrors src/utils/peerAddress.ts"""
from __future__ import annotations

from typing import Literal, TypedDict


class ParsedAddress(TypedDict):
    scheme: Literal["uds", "bridge", "other"]
    target: str


def parse_address(to: str) -> ParsedAddress:
    """Parse a URI-style address into scheme + target.

    Supported schemes:
    - ``uds:path``     → Unix domain socket
    - ``bridge:addr``  → Bridge messaging
    - ``/path``        → Bare socket path (legacy UDS)
    - anything else    → 'other'
    """
    if to.startswith("uds:"):
        return ParsedAddress(scheme="uds", target=to[4:])
    if to.startswith("bridge:"):
        return ParsedAddress(scheme="bridge", target=to[7:])
    if to.startswith("/"):
        return ParsedAddress(scheme="uds", target=to)
    return ParsedAddress(scheme="other", target=to)

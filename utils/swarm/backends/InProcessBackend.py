"""Port of src/utils/swarm/backends/InProcessBackend.ts."""
from __future__ import annotations


class InProcessBackend:
    """Minimal in-process executor wrapper used by the backend registry."""

    def __init__(self, context=None):
        self.type = "in-process"
        self.context = context

    def setContext(self, context) -> None:
        self.context = context


def createInProcessBackend():
    return InProcessBackend()


create_in_process_backend = createInProcessBackend
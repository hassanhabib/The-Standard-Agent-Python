# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Sequence

from standard_agents.brokers.memories.memory_broker import MemoryBroker


class StubMemoryBroker(MemoryBroker):
    """Memory that recalls what the vector seeded it with, and remembers nothing new.

    Empty by default. A vector may seed it, which is how a POISONED memory is certified: the
    injected instruction rides the same seam a real remembered preference would.
    """

    def __init__(self, memories: Sequence[str] | None = None) -> None:
        self._memories = memories if memories is not None else []

    async def select_memories(self) -> Sequence[str]:
        return self._memories

    async def insert_memory(self, memory: str) -> None:
        return None

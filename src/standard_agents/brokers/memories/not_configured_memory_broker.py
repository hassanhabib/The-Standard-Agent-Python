# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Sequence

from standard_agents.brokers.memories.memory_broker import MemoryBroker


class NotConfiguredMemoryBroker(MemoryBroker):
    """No memory at all: nothing to recall, nowhere to store.

    What an agent composed without memory reads from, so the foundation keeps one shape rather
    than growing a nullable dependency.
    """

    async def select_memories(self) -> Sequence[str]:
        return []

    async def insert_memory(self, memory: str) -> None:
        pass

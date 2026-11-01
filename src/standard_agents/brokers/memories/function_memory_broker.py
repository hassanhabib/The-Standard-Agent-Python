# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Awaitable, Callable, Sequence

from standard_agents.brokers.memories.memory_broker import MemoryBroker


class FunctionMemoryBroker(MemoryBroker):
    """The Custom mode's substrate for memory (SPEC.md 4.8)."""

    def __init__(
            self,
            recall: Callable[[], Awaitable[Sequence[str]]],
            remember: Callable[[str], Awaitable[None]]) -> None:

        self._recall = recall
        self._remember = remember

    async def select_memories(self) -> Sequence[str]:
        return await self._recall()

    async def insert_memory(self, memory: str) -> None:
        await self._remember(memory)

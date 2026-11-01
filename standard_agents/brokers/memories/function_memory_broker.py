# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from standard_agents.brokers.memories.imemory_broker import IMemoryBroker


class FunctionMemoryBroker(IMemoryBroker):
    def __init__(self, select_all_memories: Callable[[], Awaitable[list[str]]]) -> None:
        self.select_all_memories_function = select_all_memories

    async def select_all_memories(self) -> list[str]:
        return await self.select_all_memories_function()

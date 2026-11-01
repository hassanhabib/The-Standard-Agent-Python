# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.memories.imemory_broker import IMemoryBroker


# An agent with no memory configured remembers nothing, rather than failing.
class NotConfiguredMemoryBroker(IMemoryBroker):
    async def select_all_memories(self) -> list[str]:
        return []

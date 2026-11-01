# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.brokers.memories.imemory_broker import IMemoryBroker
from standard_agents.services.foundations.memories.imemory_service import IMemoryService
from standard_agents.services.foundations.memories.memory_service_exceptions import try_catch


class MemoryService(IMemoryService):
    def __init__(
        self,
        memory_broker: IMemoryBroker,
        logging_broker: ILoggingBroker) -> None:

        self.memory_broker = memory_broker
        self.logging_broker = logging_broker

    async def retrieve_all_memories(self) -> list[str]:
        async def returning_list_function() -> list[str]:
            memories = await self.memory_broker.select_all_memories()

            return [memory for memory in memories if memory.strip() != ""]

        return await try_catch(self.logging_broker, returning_list_function)

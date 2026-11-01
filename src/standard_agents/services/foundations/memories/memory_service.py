# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Sequence

from standard_agents.brokers.files.file_broker import FileBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker


class MemoryService:
    """What the agent remembers across runs, kept by a memory broker or in a file of lines."""

    def __init__(
            self,
            *,
            logging_broker: LoggingBroker,
            memory_broker: MemoryBroker | None = None,
            file_broker: FileBroker | None = None,
            memory_path: str = "") -> None:

        self.memory_broker = memory_broker
        self.file_broker = file_broker
        self.memory_path = memory_path
        self.logging_broker = logging_broker

    async def recall_memories(self) -> Sequence[str]:
        if self.file_broker is not None:
            return await self._select_memories_from_file(self.file_broker)

        return await self.memory_broker.select_memories()

    async def remember(self, memory: str) -> None:
        await self.memory_broker.insert_memory(memory)

    async def _select_memories_from_file(self, file_broker: FileBroker) -> Sequence[str]:
        if not file_broker.file_exists(self.memory_path):
            return ()

        return await file_broker.read_all_lines(self.memory_path)

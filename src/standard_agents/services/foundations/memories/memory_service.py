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
        raise NotImplementedError

    async def remember(self, memory: str) -> None:
        raise NotImplementedError

# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from pathlib import Path

from standard_agents.brokers.memories.imemory_broker import IMemoryBroker


# One memory per line. The file is created at composition, so reading it never has to ask
# whether it exists.
class FileMemoryBroker(IMemoryBroker):
    def __init__(self, memory_path: str) -> None:
        self.memory_file = Path(memory_path)
        self.memory_file.touch(exist_ok=True)

    async def select_all_memories(self) -> list[str]:
        return self.memory_file.read_text(encoding="utf-8").splitlines()

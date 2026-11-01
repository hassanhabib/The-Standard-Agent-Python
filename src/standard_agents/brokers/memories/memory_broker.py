# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence


class MemoryBroker(ABC):
    @abstractmethod
    async def select_memories(self) -> Sequence[str]:
        ...

    @abstractmethod
    async def insert_memory(self, memory: str) -> None:
        ...

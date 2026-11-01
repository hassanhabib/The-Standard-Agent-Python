# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod


class IMemoryBroker(ABC):
    @abstractmethod
    async def select_all_memories(self) -> list[str]: ...

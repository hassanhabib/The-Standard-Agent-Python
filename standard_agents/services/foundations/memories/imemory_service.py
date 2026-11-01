# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod


class IMemoryService(ABC):
    @abstractmethod
    async def retrieve_all_memories(self) -> list[str]: ...

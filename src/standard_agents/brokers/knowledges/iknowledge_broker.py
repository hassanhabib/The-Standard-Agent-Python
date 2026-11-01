# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod


class IKnowledgeBroker(ABC):
    @abstractmethod
    async def select_knowledge(self, query: str) -> list[str]: ...

# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod


class IKnowledgeService(ABC):
    @abstractmethod
    async def retrieve_knowledge(self, query: str) -> list[str]: ...

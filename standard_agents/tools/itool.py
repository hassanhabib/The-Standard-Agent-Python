# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod


# Something the agent can do (Direction). The tool declares its own name and description,
# because the tool is what knows; the description is what the brain reads in its catalog.
class ITool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def description(self) -> str:
        return ""

    @abstractmethod
    async def execute(self, input: str) -> str: ...

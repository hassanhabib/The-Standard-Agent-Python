# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod


# Two primitives rather than one "select every skill": reading a folder of skills is iteration,
# and iteration belongs to the foundation service, not the broker.
class ISkillBroker(ABC):
    @abstractmethod
    async def select_skill_names(self) -> list[str]: ...

    @abstractmethod
    async def select_skill_content(self, skill_name: str) -> str: ...

# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod


class ISkillService(ABC):
    @abstractmethod
    async def retrieve_skills(self, route: str = "") -> str: ...

    @abstractmethod
    async def retrieve_skill_catalog(self) -> str: ...

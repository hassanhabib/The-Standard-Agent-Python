# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod

from standard_agents.models.foundations.skills.skill import Skill


# A skill source yields discrete skills, not one pre-composed blob (SPEC.md 4.1, 4.2), so the
# service can order, select and index them.
class ISkillBroker(ABC):
    @abstractmethod
    async def select_skills(self) -> list[Skill]: ...

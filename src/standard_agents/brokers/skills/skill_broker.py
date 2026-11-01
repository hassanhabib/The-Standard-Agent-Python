# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from standard_agents.models.foundations.skills.skill import Skill


class SkillBroker(ABC):
    @abstractmethod
    async def select_skills(self) -> Sequence[Skill]:
        ...

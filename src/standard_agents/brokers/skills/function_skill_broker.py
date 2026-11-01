# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from standard_agents.brokers.skills.iskill_broker import ISkillBroker
from standard_agents.models.foundations.skills.skill import Skill


class FunctionSkillBroker(ISkillBroker):
    def __init__(self, select_skills: Callable[[], Awaitable[list[Skill]]]) -> None:
        self.select_skills_function = select_skills

    async def select_skills(self) -> list[Skill]:
        return await self.select_skills_function()

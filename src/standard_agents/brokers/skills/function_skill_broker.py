# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from standard_agents.brokers.skills.iskill_broker import ISkillBroker


class FunctionSkillBroker(ISkillBroker):
    def __init__(self, select_skills: Callable[[], Awaitable[dict[str, str]]]) -> None:
        self.select_skills_function = select_skills

    async def select_skill_names(self) -> list[str]:
        return list(await self.select_skills_function())

    async def select_skill_content(self, skill_name: str) -> str:
        return (await self.select_skills_function())[skill_name]

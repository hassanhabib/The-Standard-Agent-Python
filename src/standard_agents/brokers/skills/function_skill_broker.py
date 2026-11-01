# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Awaitable, Callable, Sequence

from standard_agents.brokers.skills.iskill_broker import ISkillBroker
from standard_agents.models.foundations.skills.skill import Skill


# The Custom mode's substrate for skills (SPEC.md 4.8).
class FunctionSkillBroker(ISkillBroker):
    def __init__(self, select: Callable[[], Awaitable[Sequence[Skill]]]) -> None:
        self._select = select

    async def select_skills(self) -> Sequence[Skill]:
        return await self._select()

# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Iterable, Sequence

from standard_agents.brokers.skills.iskill_broker import ISkillBroker
from standard_agents.models.foundations.skills.skill import Skill


# Many skill sources (folders, registries, delegates) as the one stream the agent reads. The
# sources are read in registration order and their skills concatenate, so what a skill file
# relies on (earlier files establish context for later ones) holds across sources exactly as it
# holds across files within one folder.
class CompositeSkillBroker(ISkillBroker):
    def __init__(self, brokers: Iterable[ISkillBroker]) -> None:
        self._brokers: tuple[ISkillBroker, ...] = tuple(brokers)

    async def select_skills(self) -> Sequence[Skill]:
        skills: list[Skill] = []

        for broker in self._brokers:
            skills.extend(await broker.select_skills())

        return skills

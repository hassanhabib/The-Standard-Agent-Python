# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Iterable, Sequence

from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.foundations.skills.skill import Skill


class CompositeSkillBroker(SkillBroker):
    """Many skill sources (folders, registries, delegates) as the one stream the agent reads.

    The sources are read in registration order and their skills concatenate, so what a skill
    file relies on (earlier files establish context for later ones) holds across sources exactly
    as it holds across files within one folder.
    """

    def __init__(self, brokers: Iterable[SkillBroker]) -> None:
        self._brokers: tuple[SkillBroker, ...] = tuple(brokers)

    async def select_skills(self) -> Sequence[Skill]:
        skills: list[Skill] = []

        for broker in self._brokers:
            skills.extend(await broker.select_skills())

        return skills

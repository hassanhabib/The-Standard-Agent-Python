# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.foundations.skills.skill import Skill

_SKILL_SEPARATOR = "\n\n"


class SkillService:
    """The skills the agent reads, composed into one text in name order."""

    def __init__(self, *, skill_broker: SkillBroker, logging_broker: LoggingBroker) -> None:
        self.skill_broker = skill_broker
        self.logging_broker = logging_broker

    async def retrieve_skills(self, route: str = "") -> str:
        skills = await self.skill_broker.select_skills()
        selected_skills = sorted(skills, key=_ordinal_name)

        return _SKILL_SEPARATOR.join(skill.content for skill in selected_skills)


def _ordinal_name(skill: Skill) -> bytes:
    """The skill's name as StringComparer.Ordinal compares it: by UTF-16 code units."""
    return skill.name.encode("utf-16-be", errors="surrogatepass")

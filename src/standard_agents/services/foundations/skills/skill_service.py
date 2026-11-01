# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker


class SkillService:
    """The skills the agent reads, composed into one text in name order."""

    def __init__(self, *, skill_broker: SkillBroker, logging_broker: LoggingBroker) -> None:
        self.skill_broker = skill_broker
        self.logging_broker = logging_broker

    async def retrieve_skills(self, route: str = "") -> str:
        raise NotImplementedError

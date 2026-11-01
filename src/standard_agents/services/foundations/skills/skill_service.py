# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.brokers.skills.iskill_broker import ISkillBroker
from standard_agents.services.foundations.skills.iskill_service import ISkillService
from standard_agents.services.foundations.skills.skill_service_exceptions import try_catch

SKILL_SEPARATOR = "\n\n"


class SkillService(ISkillService):
    def __init__(
        self,
        skill_broker: ISkillBroker,
        logging_broker: ILoggingBroker) -> None:

        self.skill_broker = skill_broker
        self.logging_broker = logging_broker

    async def retrieve_skills(self, route: str = "") -> str:
        raise NotImplementedError

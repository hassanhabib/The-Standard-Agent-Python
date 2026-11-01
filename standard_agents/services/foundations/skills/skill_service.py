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

    # Skills are read in name order, so a deployment decides precedence by naming its files
    # (00-assistant.md before 10-calculator.md), the same way the C# framework does.
    async def retrieve_all_skills(self) -> str:
        async def returning_string_function() -> str:
            skill_names = await self.skill_broker.select_skill_names()
            skill_contents = []

            for skill_name in sorted(skill_names):
                skill_contents.append(await self.skill_broker.select_skill_content(skill_name))

            return SKILL_SEPARATOR.join(skill_contents)

        return await try_catch(self.logging_broker, returning_string_function)

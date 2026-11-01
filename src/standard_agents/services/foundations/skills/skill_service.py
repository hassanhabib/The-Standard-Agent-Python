# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.brokers.skills.iskill_broker import ISkillBroker
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.services.foundations.skills.iskill_service import ISkillService
from standard_agents.services.foundations.skills.skill_service_exceptions import try_catch

SKILL_SEPARATOR = "\n\n"
FRONTMATTER_FENCE = "---"


# A route selects the skills whose name it names. A route nothing matches selects every skill,
# so a mislabelled route costs specificity, never the agent's instructions.
def routed(skills: list[Skill], route: str) -> list[Skill]:
    matching_skills = [skill for skill in skills if route.lower() in skill.name.lower()]

    return matching_skills or skills


# A skill MAY declare its name and description between two fences at the top of its body. They
# are read, and stripped from what the brain is shown. A skill without a closing fence has no
# frontmatter; its body is kept whole.
def read_frontmatter(skill: Skill) -> Skill:
    lines = skill.content.replace("\r\n", "\n").split("\n")

    if lines[0].strip() != FRONTMATTER_FENCE:
        return skill

    closing_fences = [
        index for index in range(1, len(lines)) if lines[index].strip() == FRONTMATTER_FENCE
    ]

    if not closing_fences:
        return skill

    fields = {}

    for line in lines[1:closing_fences[0]]:
        key, separator, value = line.partition(":")

        if separator:
            fields[key.strip().lower()] = value.strip()

    return Skill(
        name=fields.get("name") or skill.name,
        description=fields.get("description", skill.description),
        content="\n".join(lines[closing_fences[0] + 1:]).lstrip("\n"))


class SkillService(ISkillService):
    def __init__(
        self,
        skill_broker: ISkillBroker,
        logging_broker: ILoggingBroker) -> None:

        self.skill_broker = skill_broker
        self.logging_broker = logging_broker

    # Skills compose into the system prompt in name order, so a deployment decides precedence by
    # naming its files (00-assistant.md before 10-calculator.md).
    async def retrieve_skills(self, route: str = "") -> str:
        async def returning_string_function() -> str:
            skills = [read_frontmatter(skill) for skill in await self.skill_broker.select_skills()]
            ordered_skills = sorted(routed(skills, route), key=lambda skill: skill.name)

            return SKILL_SEPARATOR.join(skill.content for skill in ordered_skills)

        return await try_catch(self.logging_broker, returning_string_function)

    async def retrieve_skill_catalog(self) -> str:
        raise NotImplementedError

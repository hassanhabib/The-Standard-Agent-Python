# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import dataclasses

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.services.foundations.knowledges.iknowledge_service import (
    IKnowledgeService)
from standard_agents.services.foundations.memories.imemory_service import IMemoryService
from standard_agents.services.foundations.skills.iskill_service import ISkillService
from standard_agents.services.orchestrations.data.data_orchestration_service_exceptions import (
    try_catch)
from standard_agents.services.orchestrations.data.data_orchestration_service_validations import (
    validate_context)
from standard_agents.services.orchestrations.data.idata_orchestration_service import (
    IDataOrchestrationService)

# Where a skill asks for the tool catalog to be written in, exactly as in the C# framework.
TOOLS_MARKER = "{{tools}}"


def with_new_observations(observations: tuple[str, ...], recalled: list[str]) -> tuple[str, ...]:
    new_observations = []

    for item in recalled:
        if item not in observations and item not in new_observations:
            new_observations.append(item)

    return observations + tuple(new_observations)


class DataOrchestrationService(IDataOrchestrationService):
    def __init__(
        self,
        skill_service: ISkillService,
        memory_service: IMemoryService,
        knowledge_service: IKnowledgeService,
        logging_broker: ILoggingBroker,
        tool_catalog: str = "") -> None:

        self.skill_service = skill_service
        self.memory_service = memory_service
        self.knowledge_service = knowledge_service
        self.logging_broker = logging_broker
        self.tool_catalog = tool_catalog

    # Recalled fresh every turn: memories and knowledge replace last turn's, while observations,
    # which only Direction adds to, are carried through untouched.
    async def recall(self, context: AgentContext) -> AgentContext:
        async def returning_context_function() -> AgentContext:
            validate_context(context)
            skills = await self.skill_service.retrieve_skills("")
            memories = await self.memory_service.retrieve_all_memories()
            knowledge = await self.knowledge_service.retrieve_knowledge(context.prompt)

            return dataclasses.replace(
                context,
                system_prompt=skills.replace(TOOLS_MARKER, self.tool_catalog),
                observations=with_new_observations(context.observations, memories + knowledge))

        return await try_catch(self.logging_broker, returning_context_function)

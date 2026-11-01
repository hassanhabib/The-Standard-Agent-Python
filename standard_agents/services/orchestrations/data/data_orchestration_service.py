# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.services.foundations.knowledges.iknowledge_service import (
    IKnowledgeService)
from standard_agents.services.foundations.memories.imemory_service import IMemoryService
from standard_agents.services.foundations.skills.iskill_service import ISkillService
from standard_agents.services.orchestrations.data.idata_orchestration_service import (
    IDataOrchestrationService)


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

    async def recall(self, context: AgentContext) -> AgentContext:
        raise NotImplementedError

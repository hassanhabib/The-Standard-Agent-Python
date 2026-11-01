# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import dataclasses

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.services.coordinations.runs.irun_coordination_service import (
    IRunCoordinationService)
from standard_agents.services.orchestrations.data.idata_orchestration_service import (
    IDataOrchestrationService)
from standard_agents.services.orchestrations.decision.idecision_orchestration_service import (
    IDecisionOrchestrationService)
from standard_agents.services.orchestrations.direction.idirection_orchestration_service import (
    IDirectionOrchestrationService)

DEFAULT_MAX_TURNS = 7


class RunCoordinationService(IRunCoordinationService):
    def __init__(
        self,
        data_orchestration_service: IDataOrchestrationService,
        decision_orchestration_service: IDecisionOrchestrationService,
        direction_orchestration_service: IDirectionOrchestrationService,
        logging_broker: ILoggingBroker,
        max_turns: int = DEFAULT_MAX_TURNS) -> None:

        self.data_orchestration_service = data_orchestration_service
        self.decision_orchestration_service = decision_orchestration_service
        self.direction_orchestration_service = direction_orchestration_service
        self.logging_broker = logging_broker
        self.max_turns = max_turns

    async def run(self, prompt: str) -> AgentOutcome:
        context = AgentContext(prompt=prompt)

        for turn in range(self.max_turns):
            await self.logging_broker.log_turn(turn)
            context = await self.data_orchestration_service.recall(context)
            context = await self.decision_orchestration_service.think(context)

            if context.status is AgentStatus.REVISING:
                context = dataclasses.replace(context, status=AgentStatus.WORKING)

                continue

            context = await self.direction_orchestration_service.act(context)

            if context.status is not AgentStatus.WORKING:
                return AgentOutcome(result=context.result, status=context.status)

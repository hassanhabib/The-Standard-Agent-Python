# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
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
        raise NotImplementedError

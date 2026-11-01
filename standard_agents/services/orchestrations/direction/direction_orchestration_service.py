# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.services.foundations.internal_tools.iinternal_tool_service import (
    IInternalToolService)
from standard_agents.services.foundations.returns.ireturn_service import IReturnService
from standard_agents.services.orchestrations.direction.idirection_orchestration_service import (
    IDirectionOrchestrationService)


class DirectionOrchestrationService(IDirectionOrchestrationService):
    def __init__(
        self,
        internal_tool_service: IInternalToolService,
        return_service: IReturnService,
        logging_broker: ILoggingBroker) -> None:

        self.internal_tool_service = internal_tool_service
        self.return_service = return_service
        self.logging_broker = logging_broker

    async def act(self, context: AgentContext) -> AgentContext:
        raise NotImplementedError

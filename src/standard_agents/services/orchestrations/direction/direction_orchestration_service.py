# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import dataclasses

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.services.foundations.external_tools.iexternal_tool_service import (
    IExternalToolService)
from standard_agents.services.foundations.internal_tools.iinternal_tool_service import (
    IInternalToolService)
from standard_agents.services.foundations.returns.ireturn_service import IReturnService
from standard_agents.services.orchestrations.direction.direction_orchestration_service_exceptions import (
    try_catch)
from standard_agents.services.orchestrations.direction.direction_orchestration_service_validations import (
    validate_context)
from standard_agents.services.orchestrations.direction.idirection_orchestration_service import (
    IDirectionOrchestrationService)

# The directions that end a run, and how each one ends it.
TERMINAL_STATUSES = {
    "returnresponse": AgentStatus.RESPONDED,
    "refuse": AgentStatus.REFUSED,
    "awaitinput": AgentStatus.AWAITING_INPUT
}


class DirectionOrchestrationService(IDirectionOrchestrationService):
    def __init__(
        self,
        internal_tool_service: IInternalToolService,
        external_tool_service: IExternalToolService,
        return_service: IReturnService,
        logging_broker: ILoggingBroker) -> None:

        self.internal_tool_service = internal_tool_service
        self.external_tool_service = external_tool_service
        self.return_service = return_service
        self.logging_broker = logging_broker

    async def act(self, context: AgentContext) -> AgentContext:
        async def returning_context_function() -> AgentContext:
            validate_context(context)

            return await self.act_on(context)

        return await try_catch(self.logging_broker, returning_context_function)

    # The three ways Direction can act (SPEC.md 4.3): Return, ending the run; Internal, through a
    # tool the agent owns, a name the agent owns never being sent outward; External, out across
    # the boundary. A non-terminal outcome becomes an observation and the run keeps working.
    async def act_on(self, context: AgentContext) -> AgentContext:
        if context.direction_type == "":
            return context

        terminal_status = TERMINAL_STATUSES.get(context.direction_type.lower())

        if terminal_status is not None:
            result = await self.return_service.return_payload(context.payload)

            return dataclasses.replace(context, result=result, status=terminal_status)

        if await self.internal_tool_service.handles(context.direction_type):
            outcome = await self.internal_tool_service.run(context.direction_type, context.payload)
        else:
            outcome = await self.external_tool_service.call(context.direction_type, context.payload)

        return dataclasses.replace(
            context,
            observations=context.observations + (
                f"{context.direction_type} returned: {outcome}",),
            result=outcome,
            status=AgentStatus.WORKING)

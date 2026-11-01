# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.direction.exceptions import (
    DirectionOrchestrationValidationException,
    NullAgentContextException)


async def try_catch(
    logging_broker: ILoggingBroker,
    returning_context_function: Callable[[], Awaitable[AgentContext]]) -> AgentContext:

    try:
        return await returning_context_function()
    except NullAgentContextException as null_agent_context_exception:
        raise await create_and_log_validation_exception(
            logging_broker,
            null_agent_context_exception)


async def create_and_log_validation_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> DirectionOrchestrationValidationException:

    direction_orchestration_validation_exception = DirectionOrchestrationValidationException(
        message="Direction orchestration validation error occurred, "
            + "fix the errors and try again.",
        inner_exception=exception)

    await logging_broker.log_error(direction_orchestration_validation_exception)

    return direction_orchestration_validation_exception

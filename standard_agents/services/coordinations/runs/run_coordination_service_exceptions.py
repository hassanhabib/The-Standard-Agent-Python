# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.coordinations.runs.exceptions import (
    InvalidRunException,
    RunCoordinationValidationException)


async def try_catch(
    logging_broker: ILoggingBroker,
    returning_outcome_function: Callable[[], Awaitable[AgentOutcome]]) -> AgentOutcome:

    try:
        return await returning_outcome_function()
    except InvalidRunException as invalid_run_exception:
        raise await create_and_log_validation_exception(logging_broker, invalid_run_exception)


async def create_and_log_validation_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> RunCoordinationValidationException:

    run_coordination_validation_exception = RunCoordinationValidationException(
        message="Run coordination validation error occurred, fix the errors and try again.",
        inner_exception=exception)

    await logging_broker.log_error(run_coordination_validation_exception)

    return run_coordination_validation_exception

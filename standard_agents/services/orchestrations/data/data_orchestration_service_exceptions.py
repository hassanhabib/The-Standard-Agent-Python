# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.foundations.knowledges.exceptions import (
    KnowledgeValidationException)
from standard_agents.models.orchestrations.data.exceptions import (
    DataOrchestrationDependencyValidationException,
    DataOrchestrationValidationException,
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
    # Unwrap the foundation's category and keep its local exception, so the reason the input was
    # rejected travels upward intact while the category becomes this layer's own.
    except KnowledgeValidationException as dependency_validation_exception:
        raise await create_and_log_dependency_validation_exception(
            logging_broker,
            dependency_validation_exception.inner_exception)


async def create_and_log_dependency_validation_exception(
    logging_broker: ILoggingBroker,
    exception: BaseException | None) -> DataOrchestrationDependencyValidationException:

    data_orchestration_dependency_validation_exception = (
        DataOrchestrationDependencyValidationException(
            message="Data orchestration dependency validation error occurred, "
                + "fix the errors and try again.",
            inner_exception=exception))

    await logging_broker.log_error(data_orchestration_dependency_validation_exception)

    return data_orchestration_dependency_validation_exception


async def create_and_log_validation_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> DataOrchestrationValidationException:

    data_orchestration_validation_exception = DataOrchestrationValidationException(
        message="Data orchestration validation error occurred, fix the errors and try again.",
        inner_exception=exception)

    await logging_broker.log_error(data_orchestration_validation_exception)

    return data_orchestration_validation_exception

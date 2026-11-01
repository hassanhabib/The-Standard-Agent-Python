# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.foundations.brains.exceptions import (
    BrainDependencyException,
    BrainServiceException,
    BrainValidationException)
from standard_agents.models.foundations.gates.exceptions import (
    GateDependencyException,
    GateServiceException,
    GateValidationException)
from standard_agents.models.foundations.judges.exceptions import (
    JudgeDependencyException,
    JudgeDependencyValidationException,
    JudgeServiceException,
    JudgeValidationException)
from standard_agents.models.orchestrations.decision.exceptions import (
    DecisionOrchestrationDependencyException,
    DecisionOrchestrationDependencyValidationException,
    DecisionOrchestrationServiceException,
    DecisionOrchestrationValidationException,
    FailedDecisionOrchestrationServiceException,
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
    except (
        BrainValidationException,
        GateValidationException,
        JudgeValidationException,
        JudgeDependencyValidationException) as dependency_validation_exception:

        raise await create_and_log_dependency_validation_exception(
            logging_broker,
            dependency_validation_exception.inner_exception)
    except (
        BrainDependencyException,
        BrainServiceException,
        GateDependencyException,
        GateServiceException,
        JudgeDependencyException,
        JudgeServiceException) as dependency_exception:

        raise await create_and_log_dependency_exception(
            logging_broker,
            dependency_exception.inner_exception)
    except Exception as exception:
        failed_service_exception = FailedDecisionOrchestrationServiceException(
            message="Failed decision orchestration service error occurred, contact support.",
            inner_exception=exception)

        raise await create_and_log_service_exception(logging_broker, failed_service_exception)


async def create_and_log_service_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> DecisionOrchestrationServiceException:

    decision_orchestration_service_exception = DecisionOrchestrationServiceException(
        message="Decision orchestration service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(decision_orchestration_service_exception)

    return decision_orchestration_service_exception


async def create_and_log_dependency_exception(
    logging_broker: ILoggingBroker,
    exception: BaseException | None) -> DecisionOrchestrationDependencyException:

    decision_orchestration_dependency_exception = DecisionOrchestrationDependencyException(
        message="Decision orchestration dependency error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(decision_orchestration_dependency_exception)

    return decision_orchestration_dependency_exception


async def create_and_log_dependency_validation_exception(
    logging_broker: ILoggingBroker,
    exception: BaseException | None) -> DecisionOrchestrationDependencyValidationException:

    decision_orchestration_dependency_validation_exception = (
        DecisionOrchestrationDependencyValidationException(
            message="Decision orchestration dependency validation error occurred, "
                + "fix the errors and try again.",
            inner_exception=exception))

    await logging_broker.log_error(decision_orchestration_dependency_validation_exception)

    return decision_orchestration_dependency_validation_exception


async def create_and_log_validation_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> DecisionOrchestrationValidationException:

    decision_orchestration_validation_exception = DecisionOrchestrationValidationException(
        message="Decision orchestration validation error occurred, "
            + "fix the errors and try again.",
        inner_exception=exception)

    await logging_broker.log_error(decision_orchestration_validation_exception)

    return decision_orchestration_validation_exception

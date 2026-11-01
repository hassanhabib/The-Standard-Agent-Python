# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.coordinations.runs.exceptions import (
    FailedRunCoordinationServiceException,
    InvalidRunException,
    RunCoordinationDependencyException,
    RunCoordinationDependencyValidationException,
    RunCoordinationServiceException,
    RunCoordinationValidationException)
from standard_agents.models.orchestrations.data.exceptions import (
    DataOrchestrationDependencyException,
    DataOrchestrationDependencyValidationException,
    DataOrchestrationServiceException,
    DataOrchestrationValidationException)
from standard_agents.models.orchestrations.decision.exceptions import (
    DecisionOrchestrationDependencyException,
    DecisionOrchestrationDependencyValidationException,
    DecisionOrchestrationServiceException,
    DecisionOrchestrationValidationException)
from standard_agents.models.orchestrations.direction.exceptions import (
    DirectionOrchestrationDependencyException,
    DirectionOrchestrationDependencyValidationException,
    DirectionOrchestrationServiceException,
    DirectionOrchestrationValidationException)


async def try_catch(
    logging_broker: ILoggingBroker,
    returning_outcome_function: Callable[[], Awaitable[AgentOutcome]]) -> AgentOutcome:

    try:
        return await returning_outcome_function()
    except InvalidRunException as invalid_run_exception:
        raise await create_and_log_validation_exception(logging_broker, invalid_run_exception)
    except (
        DataOrchestrationValidationException,
        DataOrchestrationDependencyValidationException,
        DecisionOrchestrationValidationException,
        DecisionOrchestrationDependencyValidationException,
        DirectionOrchestrationValidationException,
        DirectionOrchestrationDependencyValidationException) as dependency_validation_exception:

        raise await create_and_log_dependency_validation_exception(
            logging_broker,
            dependency_validation_exception.inner_exception)
    except (
        DataOrchestrationDependencyException,
        DataOrchestrationServiceException,
        DecisionOrchestrationDependencyException,
        DecisionOrchestrationServiceException,
        DirectionOrchestrationDependencyException,
        DirectionOrchestrationServiceException) as dependency_exception:

        raise await create_and_log_dependency_exception(
            logging_broker,
            dependency_exception.inner_exception)
    except Exception as exception:
        failed_service_exception = FailedRunCoordinationServiceException(
            message="Failed run coordination service error occurred, contact support.",
            inner_exception=exception)

        raise await create_and_log_service_exception(logging_broker, failed_service_exception)


async def create_and_log_service_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> RunCoordinationServiceException:

    run_coordination_service_exception = RunCoordinationServiceException(
        message="Run coordination service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(run_coordination_service_exception)

    return run_coordination_service_exception


async def create_and_log_dependency_exception(
    logging_broker: ILoggingBroker,
    exception: BaseException | None) -> RunCoordinationDependencyException:

    run_coordination_dependency_exception = RunCoordinationDependencyException(
        message="Run coordination dependency error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(run_coordination_dependency_exception)

    return run_coordination_dependency_exception


async def create_and_log_validation_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> RunCoordinationValidationException:

    run_coordination_validation_exception = RunCoordinationValidationException(
        message="Run coordination validation error occurred, fix the errors and try again.",
        inner_exception=exception)

    await logging_broker.log_error(run_coordination_validation_exception)

    return run_coordination_validation_exception


async def create_and_log_dependency_validation_exception(
    logging_broker: ILoggingBroker,
    exception: BaseException | None) -> RunCoordinationDependencyValidationException:

    run_coordination_dependency_validation_exception = (
        RunCoordinationDependencyValidationException(
            message="Run coordination dependency validation error occurred, "
                + "fix the errors and try again.",
            inner_exception=exception))

    await logging_broker.log_error(run_coordination_dependency_validation_exception)

    return run_coordination_dependency_validation_exception

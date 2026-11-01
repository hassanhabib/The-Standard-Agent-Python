# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.foundations.gates.exceptions import (
    FailedGateDependencyException,
    FailedGateServiceException,
    GateDependencyException,
    GateServiceException,
    GateValidationException,
    InvalidGateException)


async def try_catch(
    logging_broker: ILoggingBroker,
    returning_string_function: Callable[[], Awaitable[str]]) -> str:

    try:
        return await returning_string_function()
    except InvalidGateException as invalid_gate_exception:
        raise await create_and_log_validation_exception(
            logging_broker,
            invalid_gate_exception)
    # A Gate is often a model of its own: unreachable (OSError) or failing (RuntimeError).
    except (OSError, RuntimeError) as dependency_error:
        failed_gate_dependency_exception = FailedGateDependencyException(
            message="Failed gate dependency error occurred, contact support.",
            inner_exception=dependency_error)

        raise await create_and_log_dependency_exception(
            logging_broker,
            failed_gate_dependency_exception)
    except Exception as exception:
        failed_gate_service_exception = FailedGateServiceException(
            message="Failed gate service error occurred, contact support.",
            inner_exception=exception)

        raise await create_and_log_service_exception(
            logging_broker,
            failed_gate_service_exception)


async def create_and_log_service_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> GateServiceException:

    gate_service_exception = GateServiceException(
        message="Gate service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(gate_service_exception)

    return gate_service_exception


async def create_and_log_dependency_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> GateDependencyException:

    gate_dependency_exception = GateDependencyException(
        message="Gate dependency error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(gate_dependency_exception)

    return gate_dependency_exception


async def create_and_log_validation_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> GateValidationException:

    gate_validation_exception = GateValidationException(
        message="Gate validation error occurred, fix the errors and try again.",
        inner_exception=exception)

    await logging_broker.log_error(gate_validation_exception)

    return gate_validation_exception

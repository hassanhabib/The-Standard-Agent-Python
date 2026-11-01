# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.foundations.brains.exceptions import (
    BrainDependencyException,
    BrainServiceException,
    BrainValidationException,
    FailedBrainDependencyException,
    FailedBrainServiceException,
    InvalidBrainException)


async def try_catch(
    logging_broker: ILoggingBroker,
    returning_string_function: Callable[[], Awaitable[str]]) -> str:

    try:
        return await returning_string_function()
    except InvalidBrainException as invalid_brain_exception:
        raise await create_and_log_validation_exception(
            logging_broker,
            invalid_brain_exception)
    # A local model that cannot be loaded or reached (missing weights, a device gone) is a
    # configuration failure, not a bad request: critical.
    except OSError as os_error:
        failed_brain_dependency_exception = FailedBrainDependencyException(
            message="Failed brain dependency error occurred, contact support.",
            inner_exception=os_error)

        raise await create_and_log_critical_dependency_exception(
            logging_broker,
            failed_brain_dependency_exception)
    # A model that loaded but failed while generating (out of memory, a bad tensor) may be
    # transient.
    except RuntimeError as runtime_error:
        failed_brain_dependency_exception = FailedBrainDependencyException(
            message="Failed brain dependency error occurred, contact support.",
            inner_exception=runtime_error)

        raise await create_and_log_dependency_exception(
            logging_broker,
            failed_brain_dependency_exception)
    except Exception as exception:
        failed_brain_service_exception = FailedBrainServiceException(
            message="Failed brain service error occurred, contact support.",
            inner_exception=exception)

        raise await create_and_log_service_exception(
            logging_broker,
            failed_brain_service_exception)


async def create_and_log_service_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> BrainServiceException:

    brain_service_exception = BrainServiceException(
        message="Brain service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(brain_service_exception)

    return brain_service_exception


async def create_and_log_dependency_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> BrainDependencyException:

    brain_dependency_exception = BrainDependencyException(
        message="Brain dependency error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(brain_dependency_exception)

    return brain_dependency_exception


async def create_and_log_critical_dependency_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> BrainDependencyException:

    brain_dependency_exception = BrainDependencyException(
        message="Brain dependency error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_critical(brain_dependency_exception)

    return brain_dependency_exception


async def create_and_log_validation_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> BrainValidationException:

    brain_validation_exception = BrainValidationException(
        message="Brain validation error occurred, fix the errors and try again.",
        inner_exception=exception)

    await logging_broker.log_error(brain_validation_exception)

    return brain_validation_exception

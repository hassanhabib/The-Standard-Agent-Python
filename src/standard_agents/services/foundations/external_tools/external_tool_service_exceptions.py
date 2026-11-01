# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.foundations.external_tools.exceptions import (
    ExternalToolDependencyException,
    ExternalToolServiceException,
    ExternalToolValidationException,
    FailedExternalToolDependencyException,
    FailedExternalToolServiceException,
    InvalidExternalToolException)


async def try_catch(
    logging_broker: ILoggingBroker,
    returning_string_function: Callable[[], Awaitable[str]]) -> str:

    try:
        return await returning_string_function()
    except InvalidExternalToolException as invalid_external_tool_exception:
        raise await create_and_log_validation_exception(
            logging_broker,
            invalid_external_tool_exception)
    except OSError as os_error:
        failed_dependency_exception = FailedExternalToolDependencyException(
            message="Failed external tool dependency error occurred, contact support.",
            inner_exception=os_error)

        raise await create_and_log_dependency_exception(
            logging_broker,
            failed_dependency_exception)
    except Exception as exception:
        failed_service_exception = FailedExternalToolServiceException(
            message="Failed external tool service error occurred, contact support.",
            inner_exception=exception)

        raise await create_and_log_service_exception(logging_broker, failed_service_exception)


async def create_and_log_service_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> ExternalToolServiceException:

    external_tool_service_exception = ExternalToolServiceException(
        message="External tool service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(external_tool_service_exception)

    return external_tool_service_exception


async def create_and_log_dependency_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> ExternalToolDependencyException:

    external_tool_dependency_exception = ExternalToolDependencyException(
        message="External tool dependency error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(external_tool_dependency_exception)

    return external_tool_dependency_exception


async def create_and_log_validation_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> ExternalToolValidationException:

    external_tool_validation_exception = ExternalToolValidationException(
        message="External tool validation error occurred, fix the errors and try again.",
        inner_exception=exception)

    await logging_broker.log_error(external_tool_validation_exception)

    return external_tool_validation_exception

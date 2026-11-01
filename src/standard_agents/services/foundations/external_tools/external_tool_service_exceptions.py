# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.foundations.external_tools.exceptions import (
    ExternalToolValidationException,
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


async def create_and_log_validation_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> ExternalToolValidationException:

    external_tool_validation_exception = ExternalToolValidationException(
        message="External tool validation error occurred, fix the errors and try again.",
        inner_exception=exception)

    await logging_broker.log_error(external_tool_validation_exception)

    return external_tool_validation_exception

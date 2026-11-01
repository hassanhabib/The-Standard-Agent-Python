# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.foundations.internal_tools.exceptions import (
    InternalToolValidationException,
    InvalidInternalToolException)


async def try_catch_returning_boolean(
    logging_broker: ILoggingBroker,
    returning_boolean_function: Callable[[], Awaitable[bool]]) -> bool:

    try:
        return await returning_boolean_function()
    except InvalidInternalToolException as invalid_internal_tool_exception:
        raise await create_and_log_validation_exception(
            logging_broker,
            invalid_internal_tool_exception)


async def create_and_log_validation_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> InternalToolValidationException:

    internal_tool_validation_exception = InternalToolValidationException(
        message="Internal tool validation error occurred, fix the errors and try again.",
        inner_exception=exception)

    await logging_broker.log_error(internal_tool_validation_exception)

    return internal_tool_validation_exception

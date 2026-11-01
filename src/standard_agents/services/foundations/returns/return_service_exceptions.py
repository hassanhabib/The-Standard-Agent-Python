# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.foundations.returns.exceptions import (
    InvalidReturnException,
    ReturnValidationException)


# Returning touches no resource, so validation is the only thing that can go wrong here. The C#
# service also carries a catch-all; it is not ported because nothing in this routine can raise
# into it, and a branch no test can reach is not a branch TDD would write.
async def try_catch(
    logging_broker: ILoggingBroker,
    returning_string_function: Callable[[], Awaitable[str]]) -> str:

    try:
        return await returning_string_function()
    except InvalidReturnException as invalid_return_exception:
        raise await create_and_log_validation_exception(
            logging_broker,
            invalid_return_exception)


async def create_and_log_validation_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> ReturnValidationException:

    return_validation_exception = ReturnValidationException(
        message="Return validation error occurred, fix the errors and try again.",
        inner_exception=exception)

    await logging_broker.log_error(return_validation_exception)

    return return_validation_exception

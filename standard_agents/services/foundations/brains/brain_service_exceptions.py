# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.foundations.brains.exceptions import (
    BrainValidationException,
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


async def create_and_log_validation_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> BrainValidationException:

    brain_validation_exception = BrainValidationException(
        message="Brain validation error occurred, fix the errors and try again.",
        inner_exception=exception)

    await logging_broker.log_error(brain_validation_exception)

    return brain_validation_exception

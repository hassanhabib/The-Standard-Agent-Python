# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.foundations.memories.exceptions import (
    FailedMemoryDependencyException,
    MemoryDependencyException)


async def try_catch(
    logging_broker: ILoggingBroker,
    returning_list_function: Callable[[], Awaitable[list[str]]]) -> list[str]:

    try:
        return await returning_list_function()
    except OSError as os_error:
        failed_memory_dependency_exception = FailedMemoryDependencyException(
            message="Failed memory dependency error occurred, contact support.",
            inner_exception=os_error)

        raise await create_and_log_critical_dependency_exception(
            logging_broker,
            failed_memory_dependency_exception)


async def create_and_log_critical_dependency_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> MemoryDependencyException:

    memory_dependency_exception = MemoryDependencyException(
        message="Memory dependency error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_critical(memory_dependency_exception)

    return memory_dependency_exception

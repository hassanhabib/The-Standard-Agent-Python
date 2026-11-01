# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.foundations.knowledges.exceptions import (
    InvalidKnowledgeException,
    KnowledgeValidationException)


async def try_catch(
    logging_broker: ILoggingBroker,
    returning_list_function: Callable[[], Awaitable[list[str]]]) -> list[str]:

    try:
        return await returning_list_function()
    except InvalidKnowledgeException as invalid_knowledge_exception:
        raise await create_and_log_validation_exception(
            logging_broker,
            invalid_knowledge_exception)


async def create_and_log_validation_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> KnowledgeValidationException:

    knowledge_validation_exception = KnowledgeValidationException(
        message="Knowledge validation error occurred, fix the errors and try again.",
        inner_exception=exception)

    await logging_broker.log_error(knowledge_validation_exception)

    return knowledge_validation_exception

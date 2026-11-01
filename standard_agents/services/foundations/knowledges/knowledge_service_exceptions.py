# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.foundations.knowledges.exceptions import (
    FailedKnowledgeDependencyException,
    FailedKnowledgeServiceException,
    InvalidKnowledgeException,
    KnowledgeDependencyException,
    KnowledgeServiceException,
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
    # A knowledge source that cannot be read or reached right now; ConnectionError is an OSError.
    except OSError as os_error:
        failed_knowledge_dependency_exception = FailedKnowledgeDependencyException(
            message="Failed knowledge dependency error occurred, contact support.",
            inner_exception=os_error)

        raise await create_and_log_dependency_exception(
            logging_broker,
            failed_knowledge_dependency_exception)
    except Exception as exception:
        failed_knowledge_service_exception = FailedKnowledgeServiceException(
            message="Failed knowledge service error occurred, contact support.",
            inner_exception=exception)

        raise await create_and_log_service_exception(
            logging_broker,
            failed_knowledge_service_exception)


async def create_and_log_service_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> KnowledgeServiceException:

    knowledge_service_exception = KnowledgeServiceException(
        message="Knowledge service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(knowledge_service_exception)

    return knowledge_service_exception


async def create_and_log_dependency_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> KnowledgeDependencyException:

    knowledge_dependency_exception = KnowledgeDependencyException(
        message="Knowledge dependency error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(knowledge_dependency_exception)

    return knowledge_dependency_exception


async def create_and_log_validation_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> KnowledgeValidationException:

    knowledge_validation_exception = KnowledgeValidationException(
        message="Knowledge validation error occurred, fix the errors and try again.",
        inner_exception=exception)

    await logging_broker.log_error(knowledge_validation_exception)

    return knowledge_validation_exception

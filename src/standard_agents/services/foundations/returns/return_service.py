# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.foundations.returns.exceptions import (
    FailedReturnServiceException,
    InvalidReturnException,
    ReturnServiceException,
    ReturnValidationException)


class ReturnService:
    """Hands the agent's final payload back to the caller."""

    def __init__(self, *, logging_broker: LoggingBroker) -> None:
        self.logging_broker = logging_broker

    async def return_payload(self, payload: str) -> str:
        async with _handling_exceptions(self.logging_broker):
            _validate_payload(payload)

            return payload


def _validate_payload(payload: str | None) -> None:
    if not payload or payload.isspace():
        raise InvalidReturnException(
            message="Invalid return payload. Please correct the error and try again.")


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except InvalidReturnException as invalid_return_exception:
        raise await _create_and_log_validation_exception(
            logging_broker, invalid_return_exception)
    except Exception as exception:
        failed_return_service_exception = FailedReturnServiceException(
            message="Failed return service error occurred, contact support.",
            inner_exception=exception)

        raise await _create_and_log_service_exception(
            logging_broker, failed_return_service_exception)


async def _create_and_log_validation_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> ReturnValidationException:

    return_validation_exception = ReturnValidationException(
        message="Return validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(return_validation_exception)

    return return_validation_exception


async def _create_and_log_service_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> ReturnServiceException:

    return_service_exception = ReturnServiceException(
        message="Return service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(return_service_exception)

    return return_service_exception

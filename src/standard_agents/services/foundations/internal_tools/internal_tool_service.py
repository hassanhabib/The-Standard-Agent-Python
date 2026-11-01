# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.tools.tool_broker import ToolBroker
from standard_agents.models.foundations.internal_tools.exceptions import (
    FailedInternalToolDependencyException,
    FailedInternalToolServiceException,
    InternalToolDependencyException,
    InternalToolServiceException,
    InternalToolValidationException,
    InvalidInternalToolException)


class InternalToolService:
    """The tools the agent carries in process, reached through a tool broker."""

    def __init__(self, *, tool_broker: ToolBroker, logging_broker: LoggingBroker) -> None:
        self.tool_broker = tool_broker
        self.logging_broker = logging_broker

    async def handles(self, name: str) -> bool:
        async with _handling_exceptions(self.logging_broker):
            _validate_name(name)

            return await self.tool_broker.has(name)

    async def run(self, name: str, input: str) -> str:
        async with _handling_tool_exceptions(self.logging_broker):
            _validate_name(name)

            return await self.tool_broker.run(name, input)

    async def compensate(self, name: str, input: str, outcome: str) -> str:
        """Undoes what a tool did, where the tool knows how (SPEC.md 4.9).

        Returns what was done, or an empty string when the tool declared no way back.
        """
        raise NotImplementedError


def _validate_name(name: str | None) -> None:
    if not name or name.isspace():
        raise InvalidInternalToolException(
            message="Invalid internal tool. Please correct the error and try again.")


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except InvalidInternalToolException as invalid_internal_tool_exception:
        raise await _create_and_log_validation_exception(
            logging_broker, invalid_internal_tool_exception)
    except Exception as exception:
        failed_internal_tool_service_exception = FailedInternalToolServiceException(
            message="Failed internal tool service error occurred, contact support.",
            inner_exception=exception)

        raise await _create_and_log_service_exception(
            logging_broker, failed_internal_tool_service_exception)


@asynccontextmanager
async def _handling_tool_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    """Maps the failures of running a tool: whatever the tool raises is a dependency failure."""
    try:
        yield
    except InvalidInternalToolException as invalid_internal_tool_exception:
        raise await _create_and_log_validation_exception(
            logging_broker, invalid_internal_tool_exception)
    except Exception as exception:
        failed_internal_tool_dependency_exception = FailedInternalToolDependencyException(
            message="Failed internal tool dependency error occurred, contact support.",
            inner_exception=exception)

        raise await _create_and_log_dependency_exception(
            logging_broker, failed_internal_tool_dependency_exception)


async def _create_and_log_validation_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> InternalToolValidationException:

    internal_tool_validation_exception = InternalToolValidationException(
        message="Internal tool validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(internal_tool_validation_exception)

    return internal_tool_validation_exception


async def _create_and_log_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> InternalToolDependencyException:

    internal_tool_dependency_exception = InternalToolDependencyException(
        message="Internal tool dependency error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(internal_tool_dependency_exception)

    return internal_tool_dependency_exception


async def _create_and_log_service_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> InternalToolServiceException:

    internal_tool_service_exception = InternalToolServiceException(
        message="Internal tool service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(internal_tool_service_exception)

    return internal_tool_service_exception

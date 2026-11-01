# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

from restfulsense import (
    HttpRequestException,
    HttpResponseBadRequestException,
    HttpResponseForbiddenException,
    HttpResponseInternalServerErrorException,
    HttpResponseNotFoundException,
    HttpResponseServiceUnavailableException,
    HttpResponseUnauthorizedException,
    HttpResponseUrlNotFoundException)
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.mcps import mcp_json
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.models.brokers.mcps.mcp_tool import McpTool
from standard_agents.models.foundations.external_tools.exceptions import (
    ExternalToolDependencyException,
    ExternalToolDependencyValidationException,
    ExternalToolValidationException,
    FailedExternalToolDependencyException,
    InvalidExternalToolException)

# The one argument plain text travels as, for a tool that declared no schema of its own.
_INPUT_ARGUMENT_NAME = "input"


class ExternalToolService:
    """The tools the agent reaches on MCP servers, through an MCP broker."""

    def __init__(self, *, mcp_broker: McpBroker, logging_broker: LoggingBroker) -> None:
        self.mcp_broker = mcp_broker
        self.logging_broker = logging_broker

    async def call(self, name: str, input: str) -> str:
        async with _handling_exceptions(self.logging_broker):
            _validate_name(name)

            return await self.mcp_broker.call(name, _to_arguments_json(input))

    async def retrieve_tools(self) -> Sequence[McpTool]:
        """The remote tools the configured servers offer, in business language.

        What the agent may reach for, localized and categorized like every other foundation
        answer. A server that cannot be asked is a dependency failure this service names, never
        an empty catalog.
        """
        async with _handling_exceptions(self.logging_broker):
            return await self.mcp_broker.list_tools()


def _to_arguments_json(input: str) -> str:
    """The JSON object of arguments the wire takes.

    A native call already wrote one, and it goes over exactly as written; the text protocol
    produces plain text, which travels as the one argument a schema-less tool understands.
    Forcing every call into that one argument was what left typed, multi-property tools
    uncallable (principal review 2026-09-04, F-03).
    """
    if _is_json_object(input):
        return input

    return mcp_json.to_json_string({_INPUT_ARGUMENT_NAME: input})


def _is_json_object(input: str) -> bool:
    try:
        return isinstance(mcp_json.parse(input), dict)
    except json.JSONDecodeError:
        return False


def _validate_name(name: str | None) -> None:
    if not name or name.isspace():
        raise InvalidExternalToolException(
            message="Invalid external tool. Please correct the error and try again.")


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except InvalidExternalToolException as invalid_external_tool_exception:
        raise await _create_and_log_validation_exception(
            logging_broker, invalid_external_tool_exception)
    except HttpResponseBadRequestException as http_response_bad_request_exception:
        invalid_external_tool_exception = InvalidExternalToolException(
            message="Invalid external tool request. Please correct the error and try again.")

        invalid_external_tool_exception.add_data(http_response_bad_request_exception.data)

        raise await _create_and_log_dependency_validation_exception(
            logging_broker, invalid_external_tool_exception)
    except (
            HttpResponseUnauthorizedException,
            HttpResponseForbiddenException,
            HttpResponseNotFoundException,
            HttpResponseUrlNotFoundException,
            HttpRequestException) as critical_dependency_exception:

        raise await _create_and_log_critical_dependency_exception(
            logging_broker, critical_dependency_exception)
    except (
            HttpResponseInternalServerErrorException,
            HttpResponseServiceUnavailableException) as dependency_exception:

        raise await _create_and_log_dependency_exception(logging_broker, dependency_exception)


async def _create_and_log_validation_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> ExternalToolValidationException:

    external_tool_validation_exception = ExternalToolValidationException(
        message="External tool validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(external_tool_validation_exception)

    return external_tool_validation_exception


async def _create_and_log_dependency_validation_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> ExternalToolDependencyValidationException:

    external_tool_dependency_validation_exception = ExternalToolDependencyValidationException(
        message="External tool dependency validation error occurred, "
                "fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(external_tool_dependency_validation_exception)

    return external_tool_dependency_validation_exception


async def _create_and_log_critical_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> ExternalToolDependencyException:

    external_tool_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_critical(external_tool_dependency_exception)

    return external_tool_dependency_exception


async def _create_and_log_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> ExternalToolDependencyException:

    external_tool_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_error(external_tool_dependency_exception)

    return external_tool_dependency_exception


def _create_dependency_exception(exception: Exception) -> ExternalToolDependencyException:
    failed_external_tool_dependency_exception = FailedExternalToolDependencyException(
        message="Failed external tool dependency error occurred, contact support.",
        inner_exception=exception)

    return ExternalToolDependencyException(
        message="External tool dependency error occurred, contact support.",
        inner_exception=failed_external_tool_dependency_exception)

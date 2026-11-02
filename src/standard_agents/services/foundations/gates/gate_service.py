# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator
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
from standard_agents.brokers.classifiers.classifier_broker import ClassifierBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.foundations.gates.exceptions import (
    FailedGateDependencyException,
    FailedGateServiceException,
    GateDependencyException,
    GateDependencyValidationException,
    GateServiceException,
    GateValidationException,
    InvalidGateException)
from xeptions import Xeption

# Sent to the model byte for byte as the C# framework sends it, so the dash in it is the same
# U+2014 the C# rubric carries, written as an escape.
_CONFLICT_RUBRIC = (
    "You review an AI agent's active skill instructions for a DIRECT CONTRADICTION \u2014 two "
    "instructions that cannot both be obeyed at once, for example 'answer in Arabic' versus "
    "'answer in English'. If such a contradiction exists, reply with a single line in the "
    "form: CONFLICT: <short label> | <instruction> || <short label> | <instruction>. If there "
    "is no contradiction, reply with a single word: NONE.")


class GateService:
    """The Gate: screens the raw task, and checks active skill instructions for a contradiction.

    The Gate screens the raw task, so it sees exactly what redaction exists to hide, and it may
    run on a different host than the Brain (SPEC.md 4.6). That redaction is a decoration on the
    classifier below, applied at composition, so this service holds one broker.
    """

    def __init__(
            self,
            *,
            classifier_broker: ClassifierBroker,
            logging_broker: LoggingBroker) -> None:

        self.classifier_broker = classifier_broker
        self.logging_broker = logging_broker

    async def screen(self, input: str) -> str:
        async with _handling_exceptions(self.logging_broker):
            _validate_screen(input)

            return await self.classifier_broker.classify(input)

    async def detect_conflict(self, instructions: str) -> str:
        async with _handling_exceptions(self.logging_broker):
            _validate_screen(instructions)

            return await self.classifier_broker.assess(_CONFLICT_RUBRIC, instructions)


def _validate_screen(input: str | None) -> None:
    if not input or input.isspace():
        raise InvalidGateException(
            message="Invalid gate input. Please correct the error and try again.")


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except InvalidGateException as invalid_gate_exception:
        raise await _create_and_log_validation_exception(logging_broker, invalid_gate_exception)
    except HttpResponseBadRequestException as http_response_bad_request_exception:
        invalid_gate_exception = InvalidGateException(
            message="Invalid gate request. Please correct the error and try again.")

        invalid_gate_exception.add_data(http_response_bad_request_exception.data)

        raise await _create_and_log_dependency_validation_exception(
            logging_broker, invalid_gate_exception)
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
    except Exception as exception:
        failed_gate_service_exception = FailedGateServiceException(
            message="Failed gate service error occurred, contact support.",
            inner_exception=exception)

        raise await _create_and_log_service_exception(
            logging_broker, failed_gate_service_exception)


async def _create_and_log_validation_exception(
        logging_broker: LoggingBroker,
        exception: Xeption) -> GateValidationException:

    gate_validation_exception = GateValidationException(
        message="Gate validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(gate_validation_exception)

    return gate_validation_exception


async def _create_and_log_dependency_validation_exception(
        logging_broker: LoggingBroker,
        exception: Xeption) -> GateDependencyValidationException:

    gate_dependency_validation_exception = GateDependencyValidationException(
        message="Gate dependency validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(gate_dependency_validation_exception)

    return gate_dependency_validation_exception


async def _create_and_log_critical_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> GateDependencyException:

    gate_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_critical(gate_dependency_exception)

    return gate_dependency_exception


async def _create_and_log_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> GateDependencyException:

    gate_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_error(gate_dependency_exception)

    return gate_dependency_exception


def _create_dependency_exception(exception: Exception) -> GateDependencyException:
    failed_gate_dependency_exception = FailedGateDependencyException(
        message="Failed gate dependency error occurred, contact support.",
        inner_exception=exception)

    return GateDependencyException(
        message="Gate dependency error occurred, contact support.",
        inner_exception=failed_gate_dependency_exception)


async def _create_and_log_service_exception(
        logging_broker: LoggingBroker,
        exception: Xeption) -> GateServiceException:

    gate_service_exception = GateServiceException(
        message="Gate service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(gate_service_exception)

    return gate_service_exception

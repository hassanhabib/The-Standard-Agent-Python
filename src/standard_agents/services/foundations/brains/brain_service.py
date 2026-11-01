# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from restfulsense.exceptions import (
    HttpRequestException,
    HttpResponseBadRequestException,
    HttpResponseForbiddenException,
    HttpResponseInternalServerErrorException,
    HttpResponseNotFoundException,
    HttpResponseServiceUnavailableException,
    HttpResponseUnauthorizedException,
    HttpResponseUrlNotFoundException)
from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.generators.generator_broker_v1 import GeneratorBrokerV1
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.models.foundations.brains.exceptions import (
    BrainDependencyException,
    BrainDependencyValidationException,
    BrainServiceException,
    BrainValidationException,
    FailedBrainDependencyException,
    FailedBrainServiceException,
    InvalidBrainException,
    UnreachableBrainException)


class BrainService:
    """One broker role, versioned.

    Redaction and retry used to be held here as two more brokers; both are now decorations
    applied to the generator at composition, so this service knows about neither and cannot
    forget either (docs/architecture-alignment.md).
    """

    def __init__(
            self,
            *,
            generator_broker: GeneratorBroker,
            logging_broker: LoggingBroker,
            generator_broker_v1: GeneratorBrokerV1 | None = None) -> None:

        self.generator_broker = generator_broker
        self.logging_broker = logging_broker
        self.generator_broker_v1 = generator_broker_v1

    async def generate(
            self,
            system_prompt: str,
            user_prompt: str,
            *,
            inference: ResolvedInference | None = None) -> str:

        async with _handling_exceptions(self.logging_broker):
            _validate_user_prompt(user_prompt)

            return await self.generator_broker.generate(system_prompt, user_prompt)

    async def generate_stream(
            self,
            system_prompt: str,
            user_prompt: str,
            *,
            inference: ResolvedInference | None = None) -> AsyncIterator[str]:

        async with _handling_stream_exceptions(self.logging_broker):
            _validate_user_prompt(user_prompt)
            tokens = self.generator_broker.generate_stream(system_prompt, user_prompt)

        async for token in tokens:
            yield token


def _validate_user_prompt(user_prompt: str | None) -> None:
    if not user_prompt or user_prompt.isspace():
        raise InvalidBrainException(
            message="Invalid brain input. Please correct the error and try again.")


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except InvalidBrainException as invalid_brain_exception:
        raise await _create_and_log_validation_exception(
            logging_broker, invalid_brain_exception)
    except HttpResponseBadRequestException as http_response_bad_request_exception:
        invalid_brain_exception = InvalidBrainException(
            message="Invalid brain request. Please correct the error and try again.")

        invalid_brain_exception.add_data(http_response_bad_request_exception.data)

        raise await _create_and_log_dependency_validation_exception(
            logging_broker, invalid_brain_exception)
    except (
            HttpResponseUnauthorizedException,
            HttpResponseForbiddenException,
            HttpResponseNotFoundException,
            HttpResponseUrlNotFoundException) as critical_dependency_exception:

        raise await _create_and_log_critical_dependency_exception(
            logging_broker, critical_dependency_exception)
    except (
            HttpResponseInternalServerErrorException,
            HttpResponseServiceUnavailableException) as dependency_exception:

        raise await _create_and_log_dependency_exception(logging_broker, dependency_exception)
    except HttpRequestException as http_request_exception:
        raise await _create_and_log_unreachable_exception(
            logging_broker, http_request_exception)
    except Exception as exception:
        raise await _create_and_log_service_exception(
            logging_broker, _create_failed_service_exception(exception))


@asynccontextmanager
async def _handling_stream_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except InvalidBrainException as invalid_brain_exception:
        raise await _create_and_log_validation_exception(
            logging_broker, invalid_brain_exception)


async def _create_and_log_validation_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> BrainValidationException:

    brain_validation_exception = BrainValidationException(
        message="Brain validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(brain_validation_exception)

    return brain_validation_exception


async def _create_and_log_dependency_validation_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> BrainDependencyValidationException:

    brain_dependency_validation_exception = BrainDependencyValidationException(
        message="Brain dependency validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(brain_dependency_validation_exception)

    return brain_dependency_validation_exception


async def _create_and_log_unreachable_exception(
        logging_broker: LoggingBroker,
        http_request_exception: HttpRequestException) -> BrainDependencyException:
    """Nothing answered at all (SPEC.md 4.10, v1.14).

    A refused connection, a name that resolves to nothing, a request that never left the
    machine. Localised to a sentence about the address rather than "contact support", because
    the person's next step is the address and whatever should be listening at it. The native
    fault stays as the inner exception for whoever investigates, and it is still critical: a
    brain that cannot be reached is configuration.
    """
    unreachable_brain_exception = UnreachableBrainException(
        message="Nothing answered at the brain's address. Check that the address is right "
            "and that the service is running.",
        inner_exception=http_request_exception)

    brain_dependency_exception = BrainDependencyException(
        message="Brain dependency error occurred, contact support.",
        inner_exception=unreachable_brain_exception)

    await logging_broker.log_critical(brain_dependency_exception)

    return brain_dependency_exception


async def _create_and_log_critical_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> BrainDependencyException:

    brain_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_critical(brain_dependency_exception)

    return brain_dependency_exception


async def _create_and_log_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> BrainDependencyException:

    brain_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_error(brain_dependency_exception)

    return brain_dependency_exception


def _create_dependency_exception(exception: Exception) -> BrainDependencyException:
    failed_brain_dependency_exception = FailedBrainDependencyException(
        message="Failed brain dependency error occurred, contact support.",
        inner_exception=exception)

    return BrainDependencyException(
        message="Brain dependency error occurred, contact support.",
        inner_exception=failed_brain_dependency_exception)


def _create_failed_service_exception(exception: Exception) -> FailedBrainServiceException:
    return FailedBrainServiceException(
        message="Failed brain service error occurred, contact support.",
        inner_exception=exception)


async def _create_and_log_service_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> BrainServiceException:

    brain_service_exception = BrainServiceException(
        message="Brain service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(brain_service_exception)

    return brain_service_exception

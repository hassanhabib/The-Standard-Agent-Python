# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.generators.generator_broker_v1 import GeneratorBrokerV1
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.models.foundations.brains.exceptions import (
    BrainValidationException,
    InvalidBrainException)


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

        async for token in self.generator_broker.generate_stream(system_prompt, user_prompt):
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


async def _create_and_log_validation_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> BrainValidationException:

    brain_validation_exception = BrainValidationException(
        message="Brain validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(brain_validation_exception)

    return brain_validation_exception

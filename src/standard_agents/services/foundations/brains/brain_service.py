# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator

from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.generators.generator_broker_v1 import GeneratorBrokerV1
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference


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

        return await self.generator_broker.generate(system_prompt, user_prompt)

    async def generate_stream(
            self,
            system_prompt: str,
            user_prompt: str,
            *,
            inference: ResolvedInference | None = None) -> AsyncIterator[str]:

        async for token in self.generator_broker.generate_stream(system_prompt, user_prompt):
            yield token

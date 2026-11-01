# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable

from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.brokers.generators.generator_broker import GeneratorBroker


class FunctionGeneratorBroker(GeneratorBroker):
    def __init__(self, generate: Callable[[str, str], Awaitable[str]]) -> None:
        self._generate = generate

    async def generate(
            self,
            system_prompt: str,
            user_prompt: str,
            *,
            inference: ResolvedInference | None = None) -> str:

        return await self._generate(system_prompt, user_prompt)

    async def generate_stream(
            self,
            system_prompt: str,
            user_prompt: str,
            *,
            inference: ResolvedInference | None = None) -> AsyncIterator[str]:

        yield await self._generate(system_prompt, user_prompt)

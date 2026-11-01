# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import AsyncIterator, Awaitable, Callable

from standard_agents.brokers.generators.igenerator_broker import IGeneratorBroker


class FunctionGeneratorBroker(IGeneratorBroker):
    def __init__(self, generate: Callable[[str, str], Awaitable[str]]) -> None:
        self._generate = generate

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        return await self._generate(system_prompt, user_prompt)

    async def generate_stream(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        yield await self._generate(system_prompt, user_prompt)

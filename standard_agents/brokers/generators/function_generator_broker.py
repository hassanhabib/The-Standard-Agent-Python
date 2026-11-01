# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from standard_agents.brokers.generators.igenerator_broker import IGeneratorBroker


class FunctionGeneratorBroker(IGeneratorBroker):
    def __init__(self, generate: Callable[[str, str], Awaitable[str]]) -> None:
        self.generate_function = generate

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        return await self.generate_function(system_prompt, user_prompt)

# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from standard_agents.brokers.verifiers.iverifier_broker import IVerifierBroker


class FunctionVerifierBroker(IVerifierBroker):
    def __init__(self, verify: Callable[[str, str, str], Awaitable[str]]) -> None:
        self.verify_function = verify

    async def verify(self, system_prompt: str, task: str, candidate: str) -> str:
        return await self.verify_function(system_prompt, task, candidate)

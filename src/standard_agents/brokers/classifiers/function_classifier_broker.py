# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from standard_agents.brokers.classifiers.iclassifier_broker import IClassifierBroker


class FunctionClassifierBroker(IClassifierBroker):
    def __init__(self, classify: Callable[[str, str], Awaitable[str]]) -> None:
        self.classify_function = classify

    async def classify(self, system_prompt: str, input: str) -> str:
        return await self.classify_function(system_prompt, input)
